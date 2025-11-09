# M5Stack ATOM Echo - Voice AI Gateway

Real-time voice assistant powered by OpenAI's Realtime API for the M5Stack ATOM Echo (ESP32). Multiple implementation approaches with full hardware support.

## 🎯 Project Status

**Current State:** Three working implementations with different trade-offs:

- ✅ **ESP-IDF (PlatformIO)** - Full hardware support, WebSocket ready, production candidate
- ✅ **MicroPython** - Networking works, audio blocked by I2S PDM limitation  
- ✅ **Arduino** - Full hardware access, but WebSocket challenges for Realtime API

**Recommended:** ESP-IDF implementation for production use

## 📋 Features

### Hardware Support
- 🎤 **PDM Microphone** - SPM1423 working (ESP-IDF only)
- 🔊 **I2S Speaker** - NS4168 amplifier with audio playback
- 💡 **RGB LED** - SK6812 with multiple status indicators
- 🔘 **Button** - Press-to-talk and function control

### Software Features  
- 🌐 **WiFi** - Stable connection with auto-reconnect
- 🔌 **WebSocket** - Client ready for OpenAI Realtime API
- 🎙️ **Audio I/O** - PDM input, I2S output with proper buffering
- 📡 **Base64** - Audio encoding for API transmission
- 🔐 **TLS/SSL** - Secure connections

## 🛠️ Hardware

**Device:** M5Stack ATOM Echo (ESP32-PICO-D4)

**Specifications:**
- ESP32-PICO-D4: 240MHz Dual Core, 4MB Flash
- SPM1423 PDM Microphone (GPIO33=CLK, GPIO23=DATA)  
- NS4168 I2S Speaker (GPIO19=BCK, GPIO33=WS, GPIO22=DATA)
- SK6812 RGB LED (GPIO27)
- Button (GPIO39)

**Key Detail:** GPIO33 is shared between mic clock and speaker WS - handled through careful I2S channel management.

## 📁 Project Structure

\\\
m5stack-atom-echo-voice-assistant/
├── platformio-espidf/           # ⭐ ESP-IDF implementation (RECOMMENDED)
│   ├── src/main.c              # Complete working firmware
│   ├── platformio.ini          # PlatformIO configuration
│   ├── credentials.h           # WiFi/API credentials (gitignored)
│   ├── credentials.h.example   # Template for credentials
│   ├── DEPLOYMENT_STATUS.md    # Current implementation status
│   ├── PIN_CONFIGURATION.md    # Hardware wiring guide
│   └── components/             # ESP WebSocket client component
├── arduino/                     # Arduino C++ implementation
│   ├── atom_echo_voice/        # Arduino sketch
│   ├── config.h.example        # Configuration template
│   ├── SETUP_INSTRUCTIONS.md   # Arduino IDE setup guide
│   └── ARCHITECTURAL_BLOCKER.md # WebSocket limitations
├── micropython/                 # MicroPython implementation
│   ├── main.py                 # Complete networking code
│   ├── README.md               # MicroPython-specific docs
│   └── test_*.py               # Diagnostic utilities
├── server/                      # Python backend server
│   ├── main.py                 # FastAPI server
│   ├── requirements.txt        # Python dependencies
│   └── .env.example            # Server configuration template
└── firmware/                    # Legacy/experimental builds
\\\

## 🚀 Quick Start

### Prerequisites

- M5Stack ATOM Echo connected via USB
- PlatformIO installed (VS Code extension recommended)
- WiFi network (2.4GHz)
- OpenAI API key

### Option A: ESP-IDF (Recommended)

\\\ash
# 1. Clone repository
git clone https://github.com/eric-rolph/m5stack-atom-echo-voice-assistant.git
cd m5stack-atom-echo-voice-assistant/platformio-espidf

# 2. Configure credentials
cp credentials.h.example credentials.h
# Edit credentials.h with your WiFi SSID, password, and OpenAI API key

# 3. Build and upload
pio run --target upload --upload-port COM9

# 4. Monitor output
pio device monitor -b 115200
\\\

### Option B: Arduino IDE

\\\ash
# See arduino/SETUP_INSTRUCTIONS.md for detailed setup
\\\

### Option C: MicroPython

\\\ash
# See micropython/README.md - note: microphone won't work
\\\

## 🎨 LED Status Indicators

| Color | Status |
|-------|--------|
| 🔵 Blue | Initializing / Startup |
| 🟡 Yellow | Connecting to WiFi |
| 🟢 Green | Connected and Ready |
| 🟣 Magenta | Button Pressed |
| 🔴 Red | Error |

## 🔧 Configuration

### ESP-IDF (\credentials.h\)

\\\c
#define WIFI_SSID "YourWiFiName"
#define WIFI_PASSWORD "YourWiFiPassword"
#define OPENAI_API_KEY "sk-your-api-key"
#define REALTIME_MODEL "gpt-4o-realtime-preview-2024-10-01"
\\\

### Server (\.env\)

\\\ash
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
AI_PROVIDER=openai  # or gemini
TTS_PROVIDER=openai
HOST=0.0.0.0
PORT=8000
\\\

## 📊 Implementation Comparison

| Feature | ESP-IDF | Arduino | MicroPython |
|---------|---------|---------|-------------|
| PDM Mic | ✅ Full | ✅ Full | ❌ No PDM |
| I2S Speaker | ✅ Yes | ✅ Yes | ✅ Yes |
| WebSocket | ✅ Component | ⚠️ Limited | ✅ uwebsockets |
| Memory | ✅ Efficient | ⚠️ Tight | ⚠️ Limited |
| TLS/SSL | ✅ Native | ✅ Native | ✅ Native |
| Development | Medium | Easy | Easy |
| **Recommended** | **✅ Yes** | For prototypes | Learning only |

## 🐛 Known Issues & Solutions

### ESP-IDF
- ✅ All hardware working
- 🔄 WebSocket Realtime API integration in progress

### Arduino  
- ✅ Hardware fully functional
- ⚠️ WebSocket library limitations for Realtime API (see ARCHITECTURAL_BLOCKER.md)

### MicroPython
- ❌ PDM microphone unsupported (I2S driver limitation)
- ✅ All networking code functional
- Not recommended for this project

## 🔍 Technical Details

### Why ESP-IDF is Recommended

1. **Native PDM Support** - I2S driver exposes \I2S_MODE_PDM\ flag
2. **WebSocket Component** - Official esp_websocket_client with reconnection
3. **Memory Management** - Direct control over FreeRTOS heap
4. **SSL/TLS** - ESP-TLS with certificate bundle support
5. **Production Ready** - Battle-tested framework for IoT devices

### Audio Pipeline

\\\
PDM Mic → I2S RX → 16-bit PCM → Base64 → WebSocket → OpenAI
OpenAI → WebSocket → Base64 Decode → PCM → I2S TX → Speaker
\\\

### GPIO Sharing Solution

GPIO33 serves dual purpose:
- **Microphone:** PDM Clock (I2S0 RX)
- **Speaker:** Word Select/LRC (I2S1 TX)

This works because ESP32 has two I2S peripherals (I2S0, I2S1) with independent pin configurations.

## 📚 Documentation

- [DEPLOYMENT_STATUS.md](platformio-espidf/DEPLOYMENT_STATUS.md) - Current implementation details
- [PIN_CONFIGURATION.md](platformio-espidf/PIN_CONFIGURATION.md) - Complete wiring guide
- [ARCHITECTURAL_BLOCKER.md](arduino/ARCHITECTURAL_BLOCKER.md) - Arduino WebSocket challenges
- [SETUP_INSTRUCTIONS.md](arduino/SETUP_INSTRUCTIONS.md) - Arduino IDE setup
- [micropython/README.md](micropython/README.md) - MicroPython implementation notes

## 🎯 Roadmap

### Phase 1: Hardware Validation ✅
- [x] PDM microphone working
- [x] I2S speaker working  
- [x] LED control
- [x] Button input
- [x] WiFi connection

### Phase 2: API Integration 🔄
- [x] WebSocket client
- [x] Base64 encoding
- [ ] OpenAI Realtime API handshake
- [ ] Bidirectional audio streaming
- [ ] Session management

### Phase 3: Polish 📋
- [ ] Voice activity detection
- [ ] Wake word support
- [ ] OTA updates
- [ ] Battery optimization

## 🤝 Contributing

Contributions welcome! Areas of interest:
- OpenAI Realtime API integration
- Audio processing optimization
- Power management
- Documentation improvements

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

## 🙏 Acknowledgments

- **M5Stack** - Excellent hardware and examples
- **Espressif** - ESP-IDF framework and I2S drivers
- **OpenAI** - Realtime API
- **Community** - Forum posts and GitHub issues that solved PDM mysteries

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/eric-rolph/m5stack-atom-echo-voice-assistant/issues)
- **Hardware Docs:** [M5Stack ATOM Echo](https://docs.m5stack.com/en/atom/atomecho)
- **API Docs:** [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime)

---

**Status:** Active development - ESP-IDF implementation recommended for production use
