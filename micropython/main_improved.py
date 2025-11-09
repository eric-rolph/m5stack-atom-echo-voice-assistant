"""
M5Stack ATOM Echo - OpenAI Realtime API Voice Assistant
Based on aiohttp WebSocket pattern from micropython-lib
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
import usocket as socket
import ussl as ssl
import random
import struct

# Import configuration
from config_realtime import *

# ============= PIN DEFINITIONS =============
# M5Stack ATOM Echo pinout
I2S_SPEAKER_BCK = 19
I2S_SPEAKER_WS = 33
I2S_SPEAKER_DATA = 22
# Microphone shares BCK and WS with speaker
I2S_MIC_BCK = 19   # Shared with speaker
I2S_MIC_WS = 33    # Shared with speaker
I2S_MIC_DATA = 23
LED_PIN = 27
BUTTON_PIN = 39

# ============= LED STATES =============
LED_OFF = (0, 0, 0)
LED_RED = (50, 0, 0)
LED_GREEN = (0, 50, 0)
LED_YELLOW = (50, 50, 0)
LED_BLUE = (0, 0, 50)

# ============= GLOBAL VARIABLES =============
led = None
button = None
i2s_speaker = None
i2s_mic = None
wlan = None
is_recording = False

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
    
    # LED
    led = neopixel.NeoPixel(Pin(LED_PIN), 1)
    set_led(*LED_OFF)
    
    # Button
    button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
    
    # I2S for speaker (TX)
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
    
    # I2S for microphone (RX) - shares BCK and WS with speaker
    i2s_mic = I2S(
        1,
        sck=Pin(I2S_MIC_BCK),
        ws=Pin(I2S_MIC_WS),
        sd=Pin(I2S_MIC_DATA),
        mode=I2S.RX,
        bits=BITS_PER_SAMPLE,
        format=I2S.MONO,
        rate=SAMPLE_RATE,
        ibuf=20000
    )
    
    print("Hardware initialized")

def connect_wifi():
    """Connect to WiFi with proper state reset and retry handling"""
    global wlan
    print(f"Connecting to WiFi: {WIFI_SSID}")
    set_led(*LED_RED)
    
    # CRITICAL: Reset WiFi state to avoid MicroPython soft-reset issues
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)  # Deactivate first
    time.sleep(0.2)     # Allow deactivation to complete
    wlan.active(True)   # Reactivate
    
    # Wait for interface to be ready
    timeout = 5
    while not wlan.active() and timeout > 0:
        time.sleep(0.1)
        timeout -= 1
    
    if not wlan.active():
        raise OSError("WiFi interface failed to activate")
    
    # Ensure clean disconnected state
    if wlan.isconnected():
        print("Already connected, disconnecting first...")
        wlan.disconnect()
        time.sleep(0.5)
    
    # Configure reconnection behavior (5 retries before giving up)
    wlan.config(reconnects=5)
    
    # Initiate connection
    wlan.connect(WIFI_SSID, WIFI_PSK)
    
    # Wait for connection with proper status checking
    max_wait = 15
    retry = 0
    while max_wait > 0:
        if wlan.isconnected():
            print(f"\nWiFi connected! IP: {wlan.ifconfig()[0]}")
            set_led(*LED_GREEN)
            return True
        
        # Just wait and retry - simpler and more reliable
        time.sleep(1)
        max_wait -= 1
        print(".", end="")
    
    print("\nWiFi connection timeout")
    set_led(*LED_RED)
    return False

# ============= WEBSOCKET CLIENT (aiohttp pattern) =============

class RealtimeWebSocket:
    """WebSocket client using asyncio.open_connection pattern like aiohttp"""
    
    CONT = 0
    TEXT = 1
    BINARY = 2
    CLOSE = 8
    PING = 9
    PONG = 10
    
    def __init__(self):
        self.reader = None
        self.writer = None
        self.closed = False
    
    @classmethod
    def _parse_frame_header(cls, header):
        """Parse WebSocket frame header"""
        byte1, byte2 = struct.unpack("!BB", header)
        fin = bool(byte1 & 0x80)
        opcode = byte1 & 0x0F
        mask = bool(byte2 & (1 << 7))
        length = byte2 & 0x7F
        return fin, opcode, mask, length
    
    @classmethod
    def _encode_frame(cls, opcode, payload):
        """Encode WebSocket frame - CLIENT MUST MASK"""
        if opcode == cls.TEXT:
            payload = payload.encode()
        
        length = len(payload)
        fin = True
        mask = True  # Clients MUST mask
        
        # Byte 1: FIN + opcode
        byte1 = 0x80 if fin else 0
        byte1 |= opcode
        
        # Byte 2: MASK + length
        byte2 = 0x80 if mask else 0
        
        if length < 126:
            byte2 |= length
            frame = struct.pack("!BB", byte1, byte2)
        elif length < (1 << 16):
            byte2 |= 126
            frame = struct.pack("!BBH", byte1, byte2, length)
        elif length < (1 << 64):
            byte2 |= 127
            frame = struct.pack("!BBQ", byte1, byte2, length)
        else:
            raise ValueError("Payload too large")
        
        # Mask is 4 bytes
        mask_bits = struct.pack("!I", random.getrandbits(32))
        frame += mask_bits
        
        # Apply mask to payload
        payload = bytes(b ^ mask_bits[i % 4] for i, b in enumerate(payload))
        
        return frame + payload
    
    async def connect(self, url, headers=None):
        """Connect using asyncio.open_connection like aiohttp"""
        # Parse URL: wss://api.openai.com/v1/realtime?model=...
        if url.startswith("wss://"):
            use_ssl = True
            url = url[6:]
        elif url.startswith("ws://"):
            use_ssl = False
            url = url[5:]
        else:
            raise ValueError("URL must start with ws:// or wss://")
        
        # Split host and path
        if "/" in url:
            host, path = url.split("/", 1)
            path = "/" + path
        else:
            host = url
            path = "/"
        
        # Extract port
        if ":" in host:
            host, port = host.split(":")
            port = int(port)
        else:
            port = 443 if use_ssl else 80
        
        print(f"Connecting to {host}:{port}{path}")
        
        # Use asyncio.open_connection like aiohttp does
        addr_info = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)[0]
        addr = addr_info[-1]
        
        # Create socket
        sock = socket.socket(addr_info[0], addr_info[1], addr_info[2])
        sock.setblocking(False)
        
        # Connect (non-blocking)
        try:
            sock.connect(addr)
        except OSError as e:
            if e.args[0] not in (115, 119):  # EINPROGRESS, EINPROGRESS (ESP32)
                raise
        
        # Wait for connection
        await asyncio.sleep_ms(100)
        
        # Wrap with SSL if needed
        if use_ssl:
            print("Wrapping with SSL...")
            # MicroPython ssl.wrap_socket doesn't take do_handshake_on_connect
            sock = ssl.wrap_socket(sock, server_hostname=host)
            sock.setblocking(False)
            print("SSL connected")
        
        # Create StreamReader/Writer
        self.reader = asyncio.StreamReader(sock)
        self.writer = asyncio.StreamWriter(sock, {})
        
        # WebSocket handshake
        key = ubinascii.b2a_base64(bytes(random.getrandbits(8) for _ in range(16)))[:-1]
        
        request = f"GET {path} HTTP/1.1\r\n"
        request += f"Host: {host}\r\n"
        request += "Upgrade: websocket\r\n"
        request += "Connection: Upgrade\r\n"
        request += f"Sec-WebSocket-Key: {key.decode()}\r\n"
        request += "Sec-WebSocket-Version: 13\r\n"
        
        if headers:
            for name, value in headers.items():
                request += f"{name}: {value}\r\n"
        
        request += "\r\n"
        
        print("Sending handshake...")
        self.writer.write(request.encode())
        await self.writer.drain()
        
        # Read handshake response
        print("Reading handshake response...")
        line = await self.reader.readline()
        if b"101" not in line:
            raise Exception(f"Bad response: {line}")
        
        # Read headers until empty line
        while True:
            line = await self.reader.readline()
            if line == b"\r\n" or not line:
                break
        
        print("WebSocket connected!")
        self.closed = False
    
    async def receive(self):
        """Receive WebSocket message"""
        if self.closed:
            return self.CLOSE, b""
        
        # Read frame header (2 bytes)
        header = await self.reader.readexactly(2)
        if len(header) != 2:
            self.closed = True
            return self.CLOSE, b""
        
        fin, opcode, has_mask, length = self._parse_frame_header(header)
        
        # Read extended length if needed
        if length == 126:
            data = await self.reader.readexactly(2)
            length, = struct.unpack("!H", data)
        elif length == 127:
            data = await self.reader.readexactly(8)
            length, = struct.unpack("!Q", data)
        
        # Read mask if present (server shouldn't mask, but handle it)
        if has_mask:
            mask = await self.reader.readexactly(4)
        
        # Read payload
        payload = await self.reader.readexactly(length)
        
        # Unmask if needed
        if has_mask:
            payload = bytes(x ^ mask[i % 4] for i, x in enumerate(payload))
        
        # Handle opcodes
        if opcode == self.TEXT:
            return opcode, payload.decode('utf-8')
        elif opcode == self.BINARY:
            return opcode, payload
        elif opcode == self.CLOSE:
            self.closed = True
            return opcode, payload
        elif opcode == self.PING:
            # Auto-respond to ping
            await self.send(payload, self.PONG)
            return opcode, payload
        else:
            return opcode, payload
    
    async def send(self, data, opcode=None):
        """Send WebSocket message"""
        if self.closed:
            return
        
        if opcode is None:
            opcode = self.TEXT if isinstance(data, str) else self.BINARY
        
        frame = self._encode_frame(opcode, data)
        self.writer.write(frame)
        await self.writer.drain()
    
    async def close(self):
        """Close WebSocket connection"""
        if not self.closed:
            self.closed = True
            try:
                await self.send(b"", self.CLOSE)
                await asyncio.sleep_ms(100)
            except:
                pass
            finally:
                if self.writer:
                    self.writer.close()
                    await self.writer.wait_closed()

# ============= OPENAI REALTIME API =============

async def init_realtime_session(ws):
    """Initialize OpenAI Realtime session"""
    print("Initializing Realtime session...")
    set_led(*LED_BLUE)
    
    # Send session configuration
    config = {
        "type": "session.update",
        "session": {
            "modalities": ["text", "audio"],
            "instructions": SYSTEM_INSTRUCTIONS,
            "voice": "alloy",
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
            }
        }
    }
    
    await ws.send(ujson.dumps(config))
    print("Session configured")

async def stream_audio_to_openai(ws, duration_ms=5000):
    """Stream audio chunks to OpenAI"""
    global is_recording, i2s_mic
    
    print(f"Recording for {duration_ms}ms...")
    set_led(*LED_RED)
    is_recording = True
    
    chunks_sent = 0
    chunk_buffer = bytearray(CHUNK_SIZE)
    
    start_time = time.ticks_ms()
    
    first_read = True
    while time.ticks_diff(time.ticks_ms(), start_time) < duration_ms:
        if not button.value():  # Button released
            break
        
        # Read audio chunk
        bytes_read = i2s_mic.readinto(chunk_buffer)
        
        if first_read:
            print(f"[MIC] First read: {bytes_read} bytes")
            first_read = False
        
        if bytes_read > 0:
            # Base64 encode
            audio_b64 = ubinascii.b2a_base64(chunk_buffer[:bytes_read]).strip().decode()
            
            # Send to OpenAI
            message = {
                "type": "input_audio_buffer.append",
                "audio": audio_b64
            }
            
            await ws.send(ujson.dumps(message))
            chunks_sent += 1
        
        await asyncio.sleep_ms(10)
    
    # Commit the buffer
    await ws.send(ujson.dumps({"type": "input_audio_buffer.commit"}))
    
    # Request response
    await ws.send(ujson.dumps({"type": "response.create"}))
    
    print(f"Sent {chunks_sent} audio chunks")
    is_recording = False
    set_led(*LED_BLUE)

# Global flag for response completion
response_ready = False

async def handle_openai_messages(ws):
    """Background task to handle incoming messages from OpenAI"""
    global i2s_speaker, response_ready
    
    print("Message handler started")
    audio_chunks_received = 0
    
    while not ws.closed:
        try:
            opcode, data = await ws.receive()
            
            if opcode == ws.CLOSE:
                print("WebSocket closed by server")
                break
            
            if opcode != ws.TEXT:
                continue
            
            msg = ujson.loads(data)
            msg_type = msg.get("type", "")
            
            # Only log important messages to reduce clutter
            if msg_type not in ["session.created", "input_audio_buffer.speech_started", "input_audio_buffer.speech_stopped"]:
                print(f"[MSG] {msg_type}")
            
            if msg_type == "response.audio.delta":
                # Play audio chunk
                audio_b64 = msg.get("delta", "")
                if audio_b64:
                    try:
                        audio_data = ubinascii.a2b_base64(audio_b64)
                        bytes_written = i2s_speaker.write(audio_data)
                        audio_chunks_received += 1
                        set_led(*LED_GREEN)
                    except Exception as e:
                        print(f"[AUDIO ERROR] {e}")
            
            elif msg_type == "response.audio.done":
                print(f"Audio playback complete - {audio_chunks_received} chunks")
                audio_chunks_received = 0
                set_led(*LED_BLUE)
            
            elif msg_type == "response.done":
                print("Response complete")
                response_ready = True
            
            elif msg_type == "error":
                print(f"Error: {msg.get('error', {})}")
                set_led(*LED_RED)
                response_ready = True
                
        except Exception as e:
            print(f"Message handler error: {e}")
            import sys
            sys.print_exception(e)
            break
            
        await asyncio.sleep_ms(10)

async def voice_interaction():
    """Main voice interaction loop with persistent WebSocket connection"""
    global response_ready
    print("Starting voice interaction...")
    
    # Connect WebSocket
    ws = RealtimeWebSocket()
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1"
    }
    
    try:
        await ws.connect(REALTIME_URL, headers=headers)
        await init_realtime_session(ws)
        
        # Start background task to handle incoming messages
        message_task = asyncio.create_task(handle_openai_messages(ws))
        
        print("Ready! Press button to talk.")
        set_led(*LED_BLUE)
        
        while True:
            # Wait for button press
            print("Waiting for button press...")
            while button.value():
                await asyncio.sleep_ms(100)
            
            print("Button pressed! Starting audio stream...")
            set_led(*LED_YELLOW)
            
            # Clear the response ready flag
            response_ready = False
            
            try:
                # Stream audio while button held
                await stream_audio_to_openai(ws)
                print("Audio streaming complete")
                
                # Wait for response to complete
                set_led(*LED_BLUE)
                print("Waiting for response...")
                
                timeout_count = 0
                while not response_ready and timeout_count < 300:  # 30 second timeout
                    await asyncio.sleep_ms(100)
                    timeout_count += 1
                
                if response_ready:
                    print("Response received")
                else:
                    print("Response timeout")
                    set_led(*LED_RED)
                    await asyncio.sleep(1)
                
            except Exception as e:
                print(f"Interaction error: {e}")
                import sys
                sys.print_exception(e)
                set_led(*LED_RED)
                await asyncio.sleep(2)
            
            set_led(*LED_BLUE)
            gc.collect()
            print(f"Free memory: {gc.mem_free()} bytes")
    
    except Exception as e:
        print(f"Voice interaction error: {e}")
        import sys
        sys.print_exception(e)
        set_led(*LED_RED)
    
    finally:
        if ws:
            await ws.close()

# ============= MAIN =============

def main():
    """Main entry point"""
    print("=" * 50)
    print("M5Stack ATOM Echo - OpenAI Realtime API")
    print("Improved WebSocket Implementation")
    print("=" * 50)
    
    # Initialize
    init_hardware()
    
    if not connect_wifi():
        print("WiFi failed, cannot continue")
        set_led(*LED_RED)
        return
    
    # Run async voice interaction
    try:
        asyncio.run(voice_interaction())
    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        print(f"Error: {e}")
        import sys
        sys.print_exception(e)
    finally:
        set_led(*LED_OFF)

if __name__ == "__main__":
    main()
