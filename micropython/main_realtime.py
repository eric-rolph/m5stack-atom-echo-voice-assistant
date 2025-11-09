"""
M5Stack ATOM Echo - OpenAI Realtime API Voice Assistant
WebSocket-based streaming for low-latency voice interaction
"""

import machine
import time
import network
import ujson
import neopixel
import ubinascii
import uasyncio as asyncio
from machine import Pin, I2S
import gc

# Import configuration
try:
    from config_realtime import *
except:
    # Fallback if import fails - REPLACE WITH YOUR CREDENTIALS
    WIFI_SSID = "your_wifi_ssid_here"
    WIFI_PSK = "your_wifi_password_here"
    OPENAI_API_KEY = "sk-proj-your-openai-api-key-here"
    REALTIME_MODEL = "gpt-4o-realtime-preview-2024-10-01"
    REALTIME_URL = f"wss://api.openai.com/v1/realtime?model={REALTIME_MODEL}"
    SAMPLE_RATE = 24000
    BITS_PER_SAMPLE = 16
    CHANNELS = 1
    CHUNK_DURATION_MS = 200
    CHUNK_SIZE = int(SAMPLE_RATE * 2 * (CHUNK_DURATION_MS / 1000))
    SYSTEM_INSTRUCTIONS = "You are a helpful voice assistant."

# ============= PIN DEFINITIONS =============
# M5Stack ATOM Echo official pinout - DO NOT CHANGE

# Speaker (I2S TX)
I2S_SPEAKER_BCK = 19
I2S_SPEAKER_WS = 33
I2S_SPEAKER_DATA = 22

# Microphone (I2S RX / PDM)
I2S_MIC_CLK = 23
I2S_MIC_DATA = 23

# Peripherals
LED_PIN = 27
BUTTON_PIN = 39

# ============= LED STATES =============
LED_OFF = (0, 0, 0)
LED_RED = (50, 0, 0)
LED_GREEN = (0, 50, 0)
LED_YELLOW = (50, 50, 0)
LED_BLUE = (0, 0, 50)
LED_MAGENTA = (50, 0, 50)
LED_CYAN = (0, 50, 50)

# ============= GLOBAL VARIABLES =============
led = None
button = None
i2s_speaker = None
i2s_mic = None
wlan = None
ws = None
is_recording = False
is_playing = False

# ============= HELPER FUNCTIONS =============

def set_led(r, g, b):
    """Set RGB LED color"""
    global led
    if led:
        led[0] = (r, g, b)
        led.write()

def init_hardware():
    """Initialize all hardware components"""
    global led, button, i2s_speaker, i2s_mic
    
    print("Initializing hardware...")
    
    # Initialize LED
    led = neopixel.NeoPixel(Pin(LED_PIN), 1)
    set_led(*LED_RED)
    
    # Initialize button (active low with pull-up)
    button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
    
    # Initialize I2S for speaker (TX) - 24kHz for Realtime API
    i2s_speaker = I2S(
        0,
        sck=Pin(I2S_SPEAKER_BCK),
        ws=Pin(I2S_SPEAKER_WS),
        sd=Pin(I2S_SPEAKER_DATA),
        mode=I2S.TX,
        bits=BITS_PER_SAMPLE,
        format=I2S.MONO,
        rate=SAMPLE_RATE,
        ibuf=20000
    )
    
    # Initialize I2S for microphone (RX) - 24kHz for Realtime API
    i2s_mic = I2S(
        1,
        sck=Pin(I2S_MIC_CLK),
        ws=Pin(I2S_SPEAKER_WS),
        sd=Pin(I2S_MIC_DATA),
        mode=I2S.RX,
        bits=BITS_PER_SAMPLE,
        format=I2S.MONO,
        rate=SAMPLE_RATE,
        ibuf=20000
    )
    
    print("Hardware initialized")

def connect_wifi():
    """Connect to WiFi with proper reset"""
    global wlan
    print(f"Connecting to WiFi: {WIFI_SSID}")
    set_led(*LED_RED)
    
    try:
        # Reset WiFi
        try:
            wlan = network.WLAN(network.STA_IF)
            wlan.active(False)
            time.sleep(1)
        except:
            pass
        
        # Start fresh
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        time.sleep(1)
        
        if not wlan.isconnected():
            wlan.connect(WIFI_SSID, WIFI_PSK)
            
            max_wait = 15
            while not wlan.isconnected() and max_wait > 0:
                time.sleep(1)
                max_wait -= 1
                print(".", end="")
            print()
        
        if wlan.isconnected():
            print(f"WiFi connected! IP: {wlan.ifconfig()[0]}")
            set_led(*LED_GREEN)
            return True
        else:
            print("WiFi connection failed")
            set_led(*LED_RED)
            return False
    except Exception as e:
        print(f"WiFi error: {e}")
        import sys
        sys.print_exception(e)
        return False

# ============= WEBSOCKET CLIENT =============

class SimpleWebSocket:
    """Minimal WebSocket client for ESP32 - Fixed for MicroPython SSL"""
    
    def __init__(self, url, headers=None):
        self.url = url
        self.headers = headers or {}
        self.socket = None
        self.connected = False
    
    async def connect(self):
        """Connect to WebSocket server"""
        import usocket as socket
        import ussl as ssl
        
        # Parse URL
        if self.url.startswith("wss://"):
            use_ssl = True
            url = self.url[6:]
        else:
            use_ssl = False
            url = self.url[5:]
        
        host, path = url.split("/", 1)
        path = "/" + path
        
        # Extract port if specified
        if ":" in host:
            host, port = host.split(":")
            port = int(port)
        else:
            port = 443 if use_ssl else 80
        
        print(f"Connecting to {host}:{port}{path}")
        
        # Create socket
        addr = socket.getaddrinfo(host, port)[0][-1]
        sock = socket.socket()
        sock.connect(addr)
        
        if use_ssl:
            sock = ssl.wrap_socket(sock, server_hostname=host)
        
        # WebSocket handshake
        key = ubinascii.b2a_base64(b"1234567890123456").strip()
        request = f"GET {path} HTTP/1.1\r\n"
        request += f"Host: {host}\r\n"
        request += "Upgrade: websocket\r\n"
        request += "Connection: Upgrade\r\n"
        request += f"Sec-WebSocket-Key: {key.decode()}\r\n"
        request += "Sec-WebSocket-Version: 13\r\n"
        
        for name, value in self.headers.items():
            request += f"{name}: {value}\r\n"
        
        request += "\r\n"
        
        # Use write() for SSL sockets, send() for regular
        if use_ssl:
            sock.write(request.encode())
        else:
            sock.send(request.encode())
        
        # Read response
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = sock.read(1) if use_ssl else sock.recv(1)
            if chunk:
                response += chunk
        
        if b"101" not in response:
            raise Exception(f"WebSocket handshake failed: {response[:200]}")
        
        print("WebSocket connected!")
        self.socket = sock
        self.use_ssl = use_ssl
        self.connected = True
    
    async def send_text(self, message):
        """Send text message"""
        if not self.connected:
            return
        
        # WebSocket frame: FIN=1, opcode=1 (text)
        frame = bytearray([0x81])
        
        msg_bytes = message.encode()
        length = len(msg_bytes)
        
        if length < 126:
            frame.append(length)
        elif length < 65536:
            frame.append(126)
            frame.extend(length.to_bytes(2, 'big'))
        else:
            frame.append(127)
            frame.extend(length.to_bytes(8, 'big'))
        
        frame.extend(msg_bytes)
        
        # Use write() for SSL, send() for regular
        if self.use_ssl:
            self.socket.write(bytes(frame))
        else:
            self.socket.send(bytes(frame))
    
    async def recv(self):
        """Receive message (non-blocking)"""
        if not self.connected:
            return None
        
        try:
            # Set non-blocking
            self.socket.setblocking(False)
            
            # Read header
            if self.use_ssl:
                header = self.socket.read(2)
            else:
                header = self.socket.recv(2)
            
            if not header or len(header) < 2:
                return None
            
            opcode = header[0] & 0x0F
            length = header[1] & 0x7F
            
            # Read extended length
            if length == 126:
                ext = self.socket.read(2) if self.use_ssl else self.socket.recv(2)
                length = int.from_bytes(ext, 'big')
            elif length == 127:
                ext = self.socket.read(8) if self.use_ssl else self.socket.recv(8)
                length = int.from_bytes(ext, 'big')
            
            # Read payload
            payload = b""
            while len(payload) < length:
                chunk_size = min(4096, length - len(payload))
                if self.use_ssl:
                    chunk = self.socket.read(chunk_size)
                else:
                    chunk = self.socket.recv(chunk_size)
                if not chunk:
                    break
                payload += chunk
            
            if opcode == 1:  # Text
                return payload.decode()
            elif opcode == 2:  # Binary
                return payload
            
            return None
            
        except OSError:
            return None
        finally:
            self.socket.setblocking(True)
    
    def close(self):
        """Close connection"""
        if self.socket:
            self.socket.close()
        self.connected = False

# ============= REALTIME API FUNCTIONS =============

async def init_realtime_session():
    """Initialize Realtime API WebSocket session"""
    global ws
    
    try:
        print("Connecting to OpenAI Realtime API...")
        set_led(*LED_CYAN)
        
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        ws = SimpleWebSocket(REALTIME_URL, headers)
        await ws.connect()
        
        print("WebSocket connected! Sending session config...")
        
        # Send session configuration
        session_config = {
            "type": "session.update",
            "session": {
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                },
                "instructions": SYSTEM_INSTRUCTIONS
            }
        }
        
        await ws.send_text(ujson.dumps(session_config))
        print("Session configured!")
        set_led(*LED_GREEN)
        
    except Exception as e:
        print(f"Realtime API connection error: {e}")
        import sys
        sys.print_exception(e)
        set_led(*LED_RED)
        raise

async def stream_audio_to_openai():
    """Stream microphone audio to OpenAI in chunks"""
    global is_recording
    
    print("Streaming audio to OpenAI...")
    set_led(*LED_YELLOW)
    is_recording = True
    
    chunk_buffer = bytearray(CHUNK_SIZE)
    
    try:
        while is_recording and button.value() == 0:  # While button pressed
            # Read audio chunk from mic
            bytes_read = i2s_mic.readinto(chunk_buffer)
            
            if bytes_read > 0:
                # Base64 encode
                audio_b64 = ubinascii.b2a_base64(chunk_buffer[:bytes_read]).decode().strip()
                
                # Send to OpenAI
                message = {
                    "type": "input_audio_buffer.append",
                    "audio": audio_b64
                }
                
                await ws.send_text(ujson.dumps(message))
                
                # Small delay to control rate
                await asyncio.sleep_ms(10)
        
        # Button released - commit audio
        commit_msg = {"type": "input_audio_buffer.commit"}
        await ws.send_text(ujson.dumps(commit_msg))
        
        print("Audio committed, waiting for response...")
        set_led(*LED_BLUE)
        
    except Exception as e:
        print(f"Streaming error: {e}")
    finally:
        is_recording = False

async def handle_openai_messages():
    """Handle incoming messages from OpenAI"""
    global is_playing
    
    while ws and ws.connected:
        message = await ws.recv()
        
        if message:
            try:
                data = ujson.loads(message)
                msg_type = data.get("type")
                
                if msg_type == "response.audio.delta":
                    # Incoming audio chunk
                    if not is_playing:
                        print("Playing audio...")
                        set_led(*LED_MAGENTA)
                        is_playing = True
                    
                    # Decode base64 audio
                    audio_b64 = data.get("delta", "")
                    if audio_b64:
                        audio_bytes = ubinascii.a2b_base64(audio_b64)
                        i2s_speaker.write(audio_bytes)
                
                elif msg_type == "response.audio.done":
                    print("Audio playback complete")
                    is_playing = False
                    set_led(*LED_GREEN)
                
                elif msg_type == "response.done":
                    print("Response complete")
                    set_led(*LED_GREEN)
                
                elif msg_type == "error":
                    print(f"API Error: {data.get('error', {})}")
                    set_led(*LED_RED)
                
                gc.collect()
                
            except Exception as e:
                print(f"Message handling error: {e}")
        
        await asyncio.sleep_ms(10)

async def voice_interaction_loop():
    """Main voice interaction loop"""
    global is_recording
    
    button_was_pressed = False
    
    while True:
        try:
            # Check button state
            button_pressed = (button.value() == 0)
            
            if button_pressed and not button_was_pressed:
                # Button just pressed
                print("\n=== Button Pressed - Recording ===")
                asyncio.create_task(stream_audio_to_openai())
                button_was_pressed = True
            
            elif not button_pressed and button_was_pressed:
                # Button released
                is_recording = False
                button_was_pressed = False
            
            await asyncio.sleep_ms(50)
            
        except Exception as e:
            print(f"Loop error: {e}")
            set_led(*LED_RED)
            await asyncio.sleep(1)

# ============= MAIN PROGRAM =============

async def main():
    """Main async program"""
    print("\n" + "="*50)
    print("M5Stack ATOM Echo - OpenAI Realtime API")
    print("WebSocket Streaming Voice Assistant")
    print("="*50 + "\n")
    
    # Initialize hardware
    init_hardware()
    
    # Connect to WiFi
    if not connect_wifi():
        print("Cannot continue without WiFi")
        while True:
            set_led(*LED_RED)
            await asyncio.sleep(0.5)
            set_led(*LED_OFF)
            await asyncio.sleep(0.5)
    
    # Initialize Realtime API session
    await init_realtime_session()
    
    set_led(*LED_GREEN)
    print("\nReady! Press and hold button to speak.")
    print("Release button to send and get response.\n")
    
    # Start message handler and interaction loop
    asyncio.create_task(handle_openai_messages())
    await voice_interaction_loop()

# Run the async main
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("\nExiting...")
    if ws:
        ws.close()
    set_led(*LED_OFF)
