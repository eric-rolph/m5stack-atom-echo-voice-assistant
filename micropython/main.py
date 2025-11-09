"""
M5Stack ATOM Echo - Standalone OpenAI Voice Assistant
Talks directly to OpenAI API over HTTPS - NO PC SERVER REQUIRED

Hardware: M5Stack ATOM Echo (ESP32-PICO-D4)
Firmware: MicroPython with I2S + SSL/TLS support
"""

import machine
import time
import network
import urequests
import ujson
import neopixel
from machine import Pin, I2S
import gc

# Import configuration
from config import *

# ============= PIN DEFINITIONS =============
# These are the official M5Stack ATOM Echo pins from the datasheet
# DO NOT CHANGE - these are hardware-specific and cannot be reused

# Speaker (I2S TX)
I2S_SPEAKER_BCK = 19    # Bit Clock
I2S_SPEAKER_WS = 33     # Word Select / LRCK
I2S_SPEAKER_DATA = 22   # Data Out

# Microphone (I2S RX / PDM)
I2S_MIC_CLK = 23        # PDM Clock
I2S_MIC_DATA = 23       # PDM Data (shared with WS on Echo)

# Peripherals
LED_PIN = 27            # NeoPixel RGB LED (WS2812)
BUTTON_PIN = 39         # Button (active low with pull-up)

# ============= LED STATES =============
LED_OFF = (0, 0, 0)
LED_RED = (50, 0, 0)        # Boot / Error
LED_GREEN = (0, 50, 0)      # WiFi OK / Ready
LED_YELLOW = (50, 50, 0)    # Recording
LED_BLUE = (0, 0, 50)       # Sending to OpenAI
LED_MAGENTA = (50, 0, 50)   # Playing audio
LED_CYAN = (0, 50, 50)      # Processing

# ============= GLOBAL VARIABLES =============
led = None
button = None
i2s_speaker = None
i2s_mic = None

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
    set_led(*LED_RED)
    
    # Initialize LED
    led = neopixel.NeoPixel(Pin(LED_PIN), 1)
    set_led(*LED_RED)
    
    # Initialize button (active low with pull-up)
    button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
    
    # Initialize I2S for speaker (TX)
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
    
    # Initialize I2S for microphone (RX)
    i2s_mic = I2S(
        1,
        sck=Pin(I2S_MIC_CLK),
        ws=Pin(I2S_SPEAKER_WS),  # Shared WS line
        sd=Pin(I2S_MIC_DATA),
        mode=I2S.RX,
        bits=BITS_PER_SAMPLE,
        format=I2S.MONO,
        rate=SAMPLE_RATE,
        ibuf=20000
    )
    
    print("Hardware initialized")

def connect_wifi():
    """Connect to WiFi with proper cleanup"""
    global wlan
    print(f"Connecting to WiFi: {WIFI_SSID}")
    set_led(*LED_RED)
    
    try:
        # Reset WiFi if it exists
        try:
            wlan = network.WLAN(network.STA_IF)
            wlan.active(False)
            time.sleep(0.5)
        except:
            pass
        
        # Create fresh WiFi interface
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        time.sleep(0.5)
        
        if not wlan.isconnected():
            wlan.connect(WIFI_SSID, WIFI_PSK)
            
            # Wait for connection
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
        set_led(*LED_RED)
        return False

def create_wav_header(data_size):
    """Create WAV file header for raw PCM data"""
    import struct
    
    # WAV header format
    header = bytearray()
    
    # RIFF chunk
    header.extend(b'RIFF')
    header.extend(struct.pack('<I', 36 + data_size))  # File size - 8
    header.extend(b'WAVE')
    
    # fmt chunk
    header.extend(b'fmt ')
    header.extend(struct.pack('<I', 16))  # Chunk size
    header.extend(struct.pack('<H', 1))   # PCM format
    header.extend(struct.pack('<H', 1))   # Mono
    header.extend(struct.pack('<I', SAMPLE_RATE))
    header.extend(struct.pack('<I', SAMPLE_RATE * 2))  # Byte rate
    header.extend(struct.pack('<H', 2))   # Block align
    header.extend(struct.pack('<H', BITS_PER_SAMPLE))
    
    # data chunk
    header.extend(b'data')
    header.extend(struct.pack('<I', data_size))
    
    return bytes(header)

def record_audio(duration_ms=RECORDING_MS):
    """Record audio from microphone - streaming to file to avoid RAM limits"""
    print(f"Recording {duration_ms}ms of audio...")
    set_led(*LED_YELLOW)
    
    # Free memory before allocation
    gc.collect()
    
    # Use small chunk size that fits in RAM
    CHUNK_SIZE = 4096  # 4KB chunks - safe for ESP32
    
    # Calculate bytes needed: sample_rate * bytes_per_sample * (duration_ms / 1000)
    bytes_needed = SAMPLE_RATE * 2 * (duration_ms // 1000)
    
    # Record to file instead of RAM
    filename = '/audio_temp.wav'
    
    try:
        with open(filename, 'wb') as f:
            # Write WAV header first
            wav_header = create_wav_header(bytes_needed)
            f.write(wav_header)
            
            # Record in small chunks
            chunk_buffer = bytearray(CHUNK_SIZE)
            bytes_read = 0
            start_time = time.ticks_ms()
            
            while bytes_read < bytes_needed:
                if time.ticks_diff(time.ticks_ms(), start_time) > duration_ms:
                    break
                
                # Read chunk from I2S
                bytes_in_chunk = i2s_mic.readinto(chunk_buffer)
                if bytes_in_chunk:
                    # Write chunk to file immediately
                    f.write(chunk_buffer[:bytes_in_chunk])
                    bytes_read += bytes_in_chunk
        
        print(f"Recorded {bytes_read} bytes to {filename}")
        gc.collect()
        return filename
        
    except Exception as e:
        print(f"Recording error: {e}")
        return None

def build_multipart_body_from_file(audio_filename, boundary):
    """Build multipart/form-data body for Whisper API - streaming from file"""
    import os
    
    # Get file size
    file_size = os.stat(audio_filename)[6]
    
    # Build header
    header = bytearray()
    header.extend(f'--{boundary}\r\n'.encode())
    header.extend(b'Content-Disposition: form-data; name="model"\r\n\r\n')
    header.extend(f'{WHISPER_MODEL}\r\n'.encode())
    header.extend(f'--{boundary}\r\n'.encode())
    header.extend(b'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n')
    header.extend(b'Content-Type: audio/wav\r\n\r\n')
    
    # Build footer
    footer = f'\r\n--{boundary}--\r\n'.encode()
    
    # Calculate total body size
    body_size = len(header) + file_size + len(footer)
    
    return header, footer, body_size

def transcribe_audio(audio_filename):
    """Send audio to OpenAI Whisper API for transcription - memory optimized"""
    print("Transcribing audio with Whisper...")
    set_led(*LED_BLUE)
    
    if not audio_filename:
        return None
    
    url = f"{OPENAI_BASE_URL}/audio/transcriptions"
    boundary = "----WebKitFormBoundary" + str(time.ticks_ms())
    
    try:
        # Build multipart in smaller chunks to save RAM
        gc.collect()
        print(f"Free memory before: {gc.mem_free()}")
        
        # Build complete body but more carefully
        body_parts = []
        
        # Add model field
        body_parts.append(f'--{boundary}\r\n'.encode())
        body_parts.append(b'Content-Disposition: form-data; name="model"\r\n\r\n')
        body_parts.append(f'{WHISPER_MODEL}\r\n'.encode())
        
        # Add file field header
        body_parts.append(f'--{boundary}\r\n'.encode())
        body_parts.append(b'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n')
        body_parts.append(b'Content-Type: audio/wav\r\n\r\n')
        
        # Read file content
        with open(audio_filename, 'rb') as f:
            file_data = f.read()
        
        body_parts.append(file_data)
        body_parts.append(f'\r\n--{boundary}--\r\n'.encode())
        
        # Join all parts
        body = b''.join(body_parts)
        
        # Clear individual parts
        body_parts = None
        file_data = None
        gc.collect()
        
        print(f"Body size: {len(body)}, Free memory: {gc.mem_free()}")
        
        # Delete temp file
        import os
        try:
            os.remove(audio_filename)
        except:
            pass
        
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        }
        
        # Send request
        response = urequests.post(url, headers=headers, data=body)
        
        # Clear body immediately
        body = None
        gc.collect()
        
        if response.status_code == 200:
            result = ujson.loads(response.text)
            transcript = result.get("text", "")
            print(f"Transcript: {transcript}")
            response.close()
            gc.collect()
            return transcript
        else:
            print(f"Whisper API error: {response.status_code}")
            print(response.text[:200])  # Truncate error
            response.close()
            return None
            
    except Exception as e:
        print(f"Transcription error: {e}")
        return None

def get_chat_response(user_message):
    """Get AI response from OpenAI Chat API"""
    print("Getting AI response...")
    set_led(*LED_CYAN)
    
    url = f"{OPENAI_BASE_URL}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful voice assistant. Keep responses brief and conversational."},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": 150
    }
    
    try:
        response = urequests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = ujson.loads(response.text)
            ai_message = result["choices"][0]["message"]["content"]
            print(f"AI: {ai_message}")
            response.close()
            gc.collect()
            return ai_message
        else:
            print(f"Chat API error: {response.status_code}")
            print(response.text)
            response.close()
            return None
            
    except Exception as e:
        print(f"Chat error: {e}")
        return None

def text_to_speech(text):
    """Convert text to speech using OpenAI TTS API"""
    print("Generating speech...")
    set_led(*LED_BLUE)
    
    url = f"{OPENAI_BASE_URL}/audio/speech"
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Request PCM format for direct I2S playback
    # OpenAI TTS supports: mp3, opus, aac, flac, pcm
    # Use "pcm" for raw 16-bit PCM at 24kHz that we can play directly
    data = {
        "model": TTS_MODEL,
        "input": text[:500],  # Limit text length for memory
        "voice": TTS_VOICE,
        "response_format": "pcm"  # Raw PCM for direct I2S playback
    }
    
    try:
        response = urequests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            audio_data = response.content
            print(f"Received {len(audio_data)} bytes of audio")
            response.close()
            gc.collect()
            return audio_data
        else:
            print(f"TTS API error: {response.status_code}")
            print(response.text)
            response.close()
            return None
            
    except Exception as e:
        print(f"TTS error: {e}")
        return None

def play_audio(audio_data):
    """Play audio through I2S speaker"""
    print("Playing audio...")
    set_led(*LED_MAGENTA)
    
    # Play audio in chunks
    chunk_size = 1024
    offset = 0
    
    while offset < len(audio_data):
        chunk = audio_data[offset:offset + chunk_size]
        i2s_speaker.write(chunk)
        offset += chunk_size
    
    # Small delay to ensure playback completes
    time.sleep(0.5)
    print("Playback complete")
    
    gc.collect()

def voice_interaction():
    """Main voice interaction flow"""
    print("\n=== Voice Interaction Started ===")
    
    try:
        # 1. Record audio to file
        audio_filename = record_audio(RECORDING_MS)
        if not audio_filename:
            print("Recording failed")
            set_led(*LED_RED)
            time.sleep(2)
            return
        
        # 2. Transcribe with Whisper (reads from file)
        transcript = transcribe_audio(audio_filename)
        if not transcript:
            print("Transcription failed")
            set_led(*LED_RED)
            time.sleep(2)
            return
        
        print(f"User said: {transcript}")
        
        # 3. Get AI response
        ai_response = get_chat_response(transcript)
        if not ai_response:
            print("AI response failed")
            set_led(*LED_RED)
            time.sleep(2)
            return
        
        print(f"AI replied: {ai_response}")
        
        # 4. Convert to speech
        audio_response = text_to_speech(ai_response)
        if not audio_response:
            print("TTS failed")
            set_led(*LED_RED)
            time.sleep(2)
            return
        
        # 5. Play audio
        play_audio(audio_response)
        
        # Done!
        set_led(*LED_GREEN)
        print("=== Interaction Complete ===\n")
        
    except Exception as e:
        print(f"Error during interaction: {e}")
        set_led(*LED_RED)
        time.sleep(2)

# ============= MAIN PROGRAM =============

def main():
    """Main program loop"""
    print("\n" + "="*50)
    print("M5Stack ATOM Echo - OpenAI Voice Assistant")
    print("Standalone - Direct API Connection")
    print("="*50 + "\n")
    
    # Initialize hardware
    init_hardware()
    
    # Connect to WiFi
    if not connect_wifi():
        print("Cannot continue without WiFi")
        while True:
            set_led(*LED_RED)
            time.sleep(0.5)
            set_led(*LED_OFF)
            time.sleep(0.5)
    
    set_led(*LED_GREEN)
    print("\nReady! Press button to start voice interaction.")
    
    # Main loop
    button_pressed = False
    
    while True:
        try:
            # Check button state (active low)
            if button.value() == 0:  # Button pressed
                if not button_pressed:
                    button_pressed = True
                    print("\nButton pressed!")
                    voice_interaction()
            else:
                button_pressed = False
            
            # Check WiFi connection
            if not wlan.isconnected():
                print("WiFi disconnected, reconnecting...")
                connect_wifi()
            
            time.sleep(0.1)
            
        except KeyboardInterrupt:
            print("\nExiting...")
            set_led(*LED_OFF)
            break
        except Exception as e:
            print(f"Main loop error: {e}")
            set_led(*LED_RED)
            time.sleep(2)
            set_led(*LED_GREEN)

if __name__ == "__main__":
    main()
