# M5Stack Atom Echo - Voice AI Gateway

A complete voice assistant system using M5Stack Atom Echo as an audio gateway to OpenAI and Google Gemini APIs.

## Architecture

```
[M5Stack Echo] --WiFi--> [Python Server] --API--> [OpenAI/Gemini]
   Audio I/O              Voice Processing        AI Services
```

## Features

- 🎤 **Press-to-talk** voice recording
- 🗣️ **Speech-to-Text** via OpenAI Whisper
- 🤖 **AI Conversation** via ChatGPT or Gemini
- 🔊 **Text-to-Speech** via OpenAI TTS
- 💡 **LED Indicators** (status feedback)
- 🔄 **Conversation Context** memory

## Quick Start

### 1. Hardware Setup

- M5Stack Atom Echo connected via USB
- WiFi network available
- Speaker/headphones (optional, has built-in speaker)

### 2. Server Setup

```bash
cd server

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env and add your API keys

# Run server
python main.py
```

Server will start on `http://0.0.0.0:8000`

### 3. Firmware Setup

**Option A: PlatformIO (Recommended)**
```bash
cd firmware
pio run --target upload --upload-port COM9
```

**Option B: Arduino IDE**
1. Open `firmware/echo_voice_gateway.ino`
2. Install libraries: M5Atom, ArduinoJson
3. Select Board: "M5Stack Atom" or "M5StickC"
4. Update WiFi credentials in code
5. Update SERVER_URL to your computer's IP
6. Upload to COM9

### 4. Configuration

**Firmware (`echo_voice_gateway.ino`):**
```cpp
const char *WIFI_SSID = "YourWiFiName";
const char *WIFI_PASSWORD = "YourWiFiPassword";
const char *SERVER_URL = "http://192.168.1.100:8000/api/voice";
```

**Server (`.env`):**
```bash
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
AI_PROVIDER=openai  # or gemini
```

## Usage

1. **Power on** M5Stack Echo
2. **Wait for green LED** (connected and ready)
3. **Press and hold button** to record (red LED)
4. **Release button** to send (yellow LED)
5. **Listen to AI response** (blue LED)

## LED Status

- 🟢 **Green** - Ready/Idle
- 🔴 **Red** - Recording
- 🟡 **Yellow** - Processing/Sending
- 🔵 **Blue** - Playing response
- 🟣 **Purple** - Error

## API Endpoints

### `POST /api/voice`
Main voice processing endpoint
- **Input**: Raw PCM audio (16kHz, 16-bit, mono)
- **Output**: PCM audio response
- **Headers**: 
  - `X-Transcription`: What you said
  - `X-AI-Response`: What AI replied

### `GET /`
Health check

### `POST /api/clear-history`
Clear conversation context

### `GET /api/history`
View conversation history (debug)

## Troubleshooting

**WiFi won't connect:**
- Check SSID/password in firmware
- Verify 2.4GHz network (ESP32 doesn't support 5GHz)

**Server connection fails:**
- Find your computer's IP: `ipconfig` (Windows) or `ifconfig` (Mac/Linux)
- Update SERVER_URL in firmware with correct IP
- Disable firewall temporarily to test

**Audio quality issues:**
- Speak clearly and close to device
- Reduce background noise
- Increase MAX_RECORD_TIME_MS if cutting off

**API errors:**
- Verify API keys are valid
- Check API quotas/billing
- Review server logs: `python main.py`

## Development

**Add new AI provider:**
1. Add client initialization in `main.py`
2. Create `get_ai_response_<provider>()` function
3. Update AI_PROVIDER environment variable

**Change TTS voice:**
Edit in `text_to_speech()`:
```python
voice="alloy"  # alloy, echo, fable, onyx, nova, shimmer
```

**Adjust recording time:**
```cpp
#define MAX_RECORD_TIME_MS 5000  // milliseconds
```

## Requirements

### Server
- Python 3.8+
- OpenAI API key (for Whisper + TTS + ChatGPT)
- OR Gemini API key (for AI only, still needs OpenAI for Whisper/TTS)

### Firmware
- PlatformIO OR Arduino IDE
- M5Atom library
- ArduinoJson library

## License

MIT - Feel free to modify and use!

## Credits

Based on M5Stack EchoRest example
Uses OpenAI Whisper, ChatGPT, TTS APIs
Uses Google Gemini API
