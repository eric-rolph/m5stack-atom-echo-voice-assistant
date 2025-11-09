# Arduino Setup and Compilation Guide

Since Arduino IDE is not installed yet, here are your options:

## Option 1: Install Arduino IDE 2.x (Recommended - GUI)

1. **Download Arduino IDE:**
   - Visit: https://www.arduino.cc/en/software
   - Download "Arduino IDE 2.3.3 for Windows (Win 10 and newer, 64 bits)"
   - Run the installer

2. **Configure ESP32 Support:**
   - Open Arduino IDE
   - File → Preferences
   - In "Additional Board Manager URLs", add:
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Tools → Board → Boards Manager
   - Search "esp32" and install "esp32 by Espressif Systems"

3. **Install Libraries:**
   - Tools → Manage Libraries
   - Install these libraries:
     * **M5Atom** by M5Stack
     * **WebSockets** by Markus Sattler
     * **ArduinoJson** by Benoit Blanchon

4. **Open and Upload:**
   - File → Open → `C:\Users\ericr\echo-voice-gateway\arduino\atom_echo_voice\atom_echo_voice.ino`
   - Tools → Board → ESP32 Arduino → **M5Stack-ATOM**
   - Tools → Port → **COM9**
   - Click Upload (→ arrow button)
   - Open Serial Monitor (115200 baud)

## Option 2: Install Arduino CLI (Command Line)

1. **Install Arduino CLI:**
   ```powershell
   winget install ArduinoSA.CLI
   ```

2. **Configure and Install:**
   ```powershell
   cd C:\Users\ericr\echo-voice-gateway\arduino\atom_echo_voice
   
   # Add ESP32 board support
   arduino-cli config init
   arduino-cli config add board_manager.additional_urls https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   arduino-cli core update-index
   arduino-cli core install esp32:esp32
   
   # Install libraries
   arduino-cli lib install M5Atom
   arduino-cli lib install "WebSockets"
   arduino-cli lib install ArduinoJson
   
   # Compile
   arduino-cli compile --fqbn esp32:esp32:m5stack-atom atom_echo_voice.ino
   
   # Upload
   arduino-cli upload -p COM9 --fqbn esp32:esp32:m5stack-atom atom_echo_voice.ino
   
   # Monitor serial output
   arduino-cli monitor -p COM9 -c baudrate=115200
   ```

## Option 3: Use PlatformIO (VS Code Extension)

1. **Install PlatformIO:**
   - In VS Code: Extensions → Search "PlatformIO IDE" → Install
   - Restart VS Code

2. **I can create a PlatformIO project for you** if you prefer this option.

## Current Status

✅ **config.h created** with your WiFi credentials and OpenAI API key
✅ **Arduino sketch ready** at `arduino/atom_echo_voice/atom_echo_voice.ino`
✅ **base64.h library** included
✅ **Documentation** available in `arduino/README.md`

⏸️ **Arduino IDE/CLI needs installation** - choose one of the options above

## Quick Test After Upload

Once uploaded, open Serial Monitor (115200 baud) and you should see:
```
=== ATOM Echo Voice Assistant ===
Build: Arduino/ESP-IDF with PDM support
Connecting to WiFi: Everest
WiFi connected!
Setting up PDM microphone...
[WS] Connected to OpenAI Realtime API!
Setup complete - Ready!
```

Press the button to test microphone - should see non-zero audio samples!

---

**Which option would you like to proceed with?**
