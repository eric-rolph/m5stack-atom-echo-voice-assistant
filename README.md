# M5Stack ATOM Echo - OpenAI Realtime Voice Assistant# M5Stack Atom Echo - Voice AI Gateway



A standalone voice assistant for the M5Stack ATOM Echo.



## 🎯 Project Status## Architecture



**Current State:** MicroPython networking code fully functional (WiFi, WebSocket, OpenAI API integration working). **Microphone blocked** due to MicroPython's I2S driver not supporting PDM mode.```

[M5Stack Echo] --WiFi--> [Python Server] --API--> [OpenAI/Gemini]

**Next Steps:** Migration to Arduino/ESP-IDF for full PDM microphone support.   Audio I/O              Voice Processing        AI Services

```

## 📋 Features

## Features

### ✅ Working (MicroPython)

- ✅ Stable WiFi connection with automatic reconnection- 🎤 **Press-to-talk** voice recording

- ✅ WebSocket client with persistent connection- 🗣️ **Speech-to-Text** via OpenAI Whisper

- ✅ OpenAI Realtime API integration- 🤖 **AI Conversation** via ChatGPT or Gemini

- ✅ Base64 audio encoding/decoding- 🔊 **Text-to-Speech** via OpenAI TTS

- ✅ Session configuration and event handling- 💡 **LED Indicators** (status feedback)

- ✅ Button control and LED status indicators- 🔄 **Conversation Context** memory

- ✅ I2S speaker initialization

## Quick Start

### ⚠️ Blocked (MicroPython)

- ❌ PDM microphone input (I2S driver limitation)### 1. Hardware Setup



### 🚧 Planned (Arduino/ESP-IDF)- M5Stack Atom Echo connected via USB

- 🔄 Port networking code to Arduino- WiFi network available

- 🔄 Enable PDM microphone with ESP-IDF I2S driver- Speaker/headphones (optional, has built-in speaker)

- 🔄 Complete end-to-end voice interaction

### 2. Server Setup

## 🛠️ Hardware

```bash

**Device:** M5Stack ATOM Echo (ESP32-PICO-D4)cd server

- **CPU:** ESP32-PICO-D4, 240MHz Dual Core

- **Flash:** 4MB# Install dependencies

- **Microphone:** SPM1423 PDM MEMS (GPIO33=CLK, GPIO23=DATA)pip install -r requirements.txt

- **Speaker:** NS4168 I2S Amplifier (GPIO19=BCK, GPIO33=WS, GPIO22=DATA)

- **Button:** GPIO39# Configure API keys

- **LED:** SK6812 RGB (GPIO27)cp .env.example .env

# Edit .env and add your API keys

**Pinout:**

```# Run server

PDM Microphone (SPM1423):python main.py

  - Clock:  GPIO33 (shared with speaker WS)```

  - Data:   GPIO23

Server will start on `http://0.0.0.0:8000`

I2S Speaker (NS4168):

  - BCK:    GPIO19### 3. Firmware Setup

  - WS/LRC: GPIO33 (shared with mic clock)

  - DATA:   GPIO22**Option A: PlatformIO (Recommended)**

```bash

Control:cd firmware

  - Button: GPIO39pio run --target upload --upload-port COM9

  - LED:    GPIO27```

```

**Option B: Arduino IDE**

## 📁 Project Structure1. Open `firmware/echo_voice_gateway.ino`

2. Install libraries: M5Atom, ArduinoJson

```3. Select Board: "M5Stack Atom" or "M5StickC"

echo-voice-gateway/4. Update WiFi credentials in code

├── micropython/                  # MicroPython implementation5. Update SERVER_URL to your computer's IP

│   ├── config.template.py       # Configuration template6. Upload to COM9

│   ├── config_realtime.py       # Your config (gitignored)

│   ├── main_improved.py         # Complete working implementation### 4. Configuration

│   ├── main_realtime.py         # Earlier version

│   ├── test_pdm_fixed.py        # PDM microphone test**Firmware (`echo_voice_gateway.ino`):**

│   └── micropython-esp32.bin    # MicroPython v1.21.0 firmware```cpp

├── arduino/                      # Arduino/ESP-IDF (planned)const char *WIFI_SSID = "YourWiFiName";

├── circuitpython/               # CircuitPython experimentsconst char *WIFI_PASSWORD = "YourWiFiPassword";

│   └── circuitpython-*.bin      # CircuitPython firmwareconst char *SERVER_URL = "http://192.168.1.100:8000/api/voice";

├── server/                      # Development server (deprecated)```

└── docs/                        # Documentation

```**Server (`.env`):**

```bash

## 🚀 Quick Start (MicroPython)OPENAI_API_KEY=sk-...

GEMINI_API_KEY=...

### 1. PrerequisitesAI_PROVIDER=openai  # or gemini

```

```bash

pip install esptool ampy pyserial## Usage

```

1. **Power on** M5Stack Echo

### 2. Flash MicroPython2. **Wait for green LED** (connected and ready)

3. **Press and hold button** to record (red LED)

```bash4. **Release button** to send (yellow LED)

cd micropython5. **Listen to AI response** (blue LED)

python -m esptool --chip esp32 --port COM9 erase_flash

python -m esptool --port COM9 write_flash -z 0x1000 micropython-esp32.bin## LED Status

```

- 🟢 **Green** - Ready/Idle

### 3. Configure- 🔴 **Red** - Recording

- 🟡 **Yellow** - Processing/Sending

```bash- 🔵 **Blue** - Playing response

cp config.template.py config_realtime.py- 🟣 **Purple** - Error

# Edit config_realtime.py with your WiFi and OpenAI API credentials

```## API Endpoints



### 4. Upload Code### `POST /api/voice`

Main voice processing endpoint

```bash- **Input**: Raw PCM audio (16kHz, 16-bit, mono)

ampy --port COM9 put config_realtime.py- **Output**: PCM audio response

ampy --port COM9 put main_improved.py main.py- **Headers**: 

```  - `X-Transcription`: What you said

  - `X-AI-Response`: What AI replied

### 5. Test (Note: Microphone won't work in MicroPython)

### `GET /`

```bashHealth check

python -m esptool --chip esp32 --port COM9 run

# Device will connect to WiFi and OpenAI Realtime API### `POST /api/clear-history`

# Speaker works, but microphone returns zeros due to PDM limitationClear conversation context

```

### `GET /api/history`

## 🔍 Technical DetailsView conversation history (debug)



### Why MicroPython Doesn't Work for PDM## Troubleshooting



The M5Stack ATOM Echo uses a **SPM1423 PDM MEMS microphone**, which requires the ESP32's I2S peripheral to be configured in **PDM mode**. MicroPython's I2S driver (`machine.I2S`) only supports standard I2S protocol and **does not expose the `I2S_MODE_PDM` flag** needed for PDM microphones.**WiFi won't connect:**

- Check SSID/password in firmware

**Arduino/ESP-IDF Solution:**- Verify 2.4GHz network (ESP32 doesn't support 5GHz)

```cpp

// This works in Arduino/ESP-IDF but not MicroPython**Server connection fails:**

i2s_config_t i2s_config = {- Find your computer's IP: `ipconfig` (Windows) or `ifconfig` (Mac/Linux)

    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX | I2S_MODE_PDM),- Update SERVER_URL in firmware with correct IP

    // ... other config- Disable firewall temporarily to test

};

```**Audio quality issues:**

- Speak clearly and close to device

### MicroPython Achievements- Reduce background noise

- Increase MAX_RECORD_TIME_MS if cutting off

Despite the microphone limitation, we successfully implemented:

**API errors:**

1. **Stable WiFi Connection**- Verify API keys are valid

   - ESP-IDF-style reconnection handling- Check API quotas/billing

   - Automatic retry with exponential backoff- Review server logs: `python main.py`

   - Clean disconnect on errors

## Development

2. **WebSocket Client**

   - Persistent connection management**Add new AI provider:**

   - Background message handler1. Add client initialization in `main.py`

   - Automatic reconnection2. Create `get_ai_response_<provider>()` function

   - Proper SSL/TLS handling3. Update AI_PROVIDER environment variable



3. **OpenAI Realtime API****Change TTS voice:**

   - Session configurationEdit in `text_to_speech()`:

   - Base64 audio encoding```python

   - Event handling (session.created, response.audio.delta, etc.)voice="alloy"  # alloy, echo, fable, onyx, nova, shimmer

   - Authentication with API key```



4. **Audio Processing****Adjust recording time:**

   - I2S speaker initialization (working)```cpp

   - Base64 decoding of received audio#define MAX_RECORD_TIME_MS 5000  // milliseconds

   - Buffer management```



## 📚 References## Requirements



### Documentation### Server

- [M5Stack ATOM Echo Docs](https://docs.m5stack.com/en/atom/atomecho)- Python 3.8+

- [SPM1423 Datasheet](https://m5stack.oss-cn-shenzhen.aliyuncs.com/resource/docs/datasheet/core/SPM1423HM4H-B_datasheet_en.pdf)- OpenAI API key (for Whisper + TTS + ChatGPT)

- [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime)- OR Gemini API key (for AI only, still needs OpenAI for Whisper/TTS)

- [ESP32 I2S Driver](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/i2s.html)

### Firmware

### Repositories- PlatformIO OR Arduino IDE

- [M5Stack ATOM Examples](https://github.com/m5stack/M5Atom)- M5Atom library

- [M5Stack ATOM Echo Examples](https://github.com/m5stack/M5Atom/tree/master/examples/Echo)- ArduinoJson library



## 🔧 Development## License



### Serial MonitorMIT - Feel free to modify and use!

```bash

# Windows## Credits

python -c "import serial; s = serial.Serial('COM9', 115200); [print(s.read(1024).decode('utf-8', errors='ignore'), end='') for _ in range(1000)]"

Based on M5Stack EchoRest example

# Reset deviceUses OpenAI Whisper, ChatGPT, TTS APIs

python -m esptool --chip esp32 --port COM9 runUses Google Gemini API

```

### File Management
```bash
# Upload file
ampy --port COM9 put filename.py

# Download file
ampy --port COM9 get main.py

# List files
ampy --port COM9 ls

# Run REPL
ampy --port COM9 repl
```

## 🐛 Known Issues

1. **PDM Microphone Not Working (MicroPython)**
   - Root Cause: MicroPython I2S driver doesn't support PDM mode
   - Status: Confirmed with M5Stack examples and ESP-IDF documentation
   - Solution: Migrate to Arduino/ESP-IDF

2. **CircuitPython Boot Loop**
   - Attempted CircuitPython for PDM support
   - Firmware flashes but device won't boot (address 0x0 vs 0x1000 issue)
   - Not pursuing further

## 🎯 Next Steps

1. **Arduino Migration** (In Progress)
   - Set up Arduino IDE with ESP32 board support
   - Port MicroPython networking code to Arduino C++
   - Use ESP-IDF I2S driver with PDM mode for microphone
   - Implement WebSocket client (WebSocketsClient library)
   - Port OpenAI Realtime API integration
   - Test complete voice interaction loop

2. **Testing & Optimization**
   - Verify PDM microphone audio quality
   - Optimize buffer sizes for latency
   - Test extended conversations
   - Battery life optimization

3. **Features**
   - Voice activity detection (VAD)
   - Push-to-talk vs always-listening modes
   - Custom wake word
   - OTA firmware updates

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- M5Stack for excellent hardware and examples
- OpenAI for the Realtime API
- MicroPython and ESP-IDF communities
- All the forum posts and GitHub issues that helped solve PDM mysteries

## 📞 Support

For issues, questions, or contributions, please open an issue on GitHub.

---

**Note:** This project is in active development. The MicroPython implementation works for everything except the microphone. Arduino/ESP-IDF migration is required for full functionality.
