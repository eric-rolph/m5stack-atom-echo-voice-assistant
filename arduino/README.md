# Arduino Implementation with PDM Microphone Support

This directory contains the Arduino/ESP-IDF implementation for the M5Stack ATOM Echo voice assistant. This implementation uses the ESP-IDF I2S driver with the `I2S_MODE_PDM` flag to properly support the SPM1423 PDM microphone.

## Why Arduino Instead of MicroPython?

The MicroPython `machine.I2S` class only supports standard I2S protocol and does not expose the `I2S_MODE_PDM` flag needed for PDM microphones. The Arduino framework with ESP-IDF provides full access to the I2S driver, enabling proper PDM microphone operation.

## Hardware Requirements

- **M5Stack ATOM Echo**
  - ESP32-PICO-D4 v1.1 (4MB Flash)
  - SPM1423 PDM Microphone (Clock: GPIO33, Data: GPIO23)
  - NS4168 I2S Speaker (BCK: GPIO19, WS: GPIO33, Data: GPIO22)
  - Button: GPIO39
  - LED: GPIO27 (SK6812 NeoPixel)

## Setup Instructions

### 1. Install Arduino IDE

Download and install Arduino IDE 2.x from [arduino.cc](https://www.arduino.cc/en/software)

### 2. Add ESP32 Board Support

1. Open Arduino IDE
2. Go to **File → Preferences**
3. In "Additional Board Manager URLs", add:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. Go to **Tools → Board → Boards Manager**
5. Search for "esp32"
6. Install **"esp32 by Espressif Systems"**

### 3. Install Required Libraries

Go to **Tools → Manage Libraries** (or **Sketch → Include Library → Manage Libraries**)

Install the following libraries:
- **M5Atom** by M5Stack (for M5.begin(), M5.Btn, M5.dis)
- **WebSockets** by Markus Sattler (for WebSocketsClient with SSL)
- **ArduinoJson** by Benoit Blanchon (for JSON parsing and serialization)

### 4. Configure Your Credentials

1. Navigate to `arduino/atom_echo_voice/`
2. Copy `config.h.template` to `config.h`:
   ```powershell
   copy config.h.template config.h
   ```
3. Edit `config.h` and replace the placeholders:
   ```cpp
   #define WIFI_SSID "your_actual_wifi_ssid"
   #define WIFI_PASSWORD "your_actual_wifi_password"
   #define OPENAI_API_KEY "sk-proj-your-actual-openai-api-key"
   ```

**Important:** `config.h` is gitignored to protect your credentials. Never commit it to version control.

### 5. Select Board and Port

1. Connect your M5Stack ATOM Echo via USB
2. In Arduino IDE:
   - **Tools → Board → ESP32 Arduino → M5Stack-ATOM** (or "ESP32 Dev Module")
   - **Tools → Port → COM9** (or your device's port)

### 6. Compile and Upload

1. Open `arduino/atom_echo_voice/atom_echo_voice.ino`
2. Click **Verify** (✓) to compile
3. Click **Upload** (→) to flash to the device
4. Open **Serial Monitor** (115200 baud) to see output

## Testing

### Expected Boot Sequence

You should see in the Serial Monitor:
```
=== ATOM Echo Voice Assistant ===
Build: Arduino/ESP-IDF with PDM support
Connecting to WiFi: YourSSID
WiFi connected!
IP address: 192.168.x.x
Setting up PDM microphone...
PDM microphone configured successfully!
Setting up I2S speaker...
I2S speaker configured successfully!
Setting up WebSocket connection...
[WS] Connected to OpenAI Realtime API!
[WS] Session created: sess_xxxxx
Setup complete - Ready!
```

### Test PDM Microphone

1. Press the button on the ATOM Echo
2. You should see:
   ```
   [BTN] Button pressed!
   [MIC] Recording audio...
   [MIC] Read 1024 samples
   [MIC] Non-zero samples: 800 / 1024 (78.1%)
   [WS] Audio sent to OpenAI
   ```

**Success Criteria:** Non-zero samples should be > 50% (proving PDM microphone works!)

### LED Status Indicators

- **Blue:** Initializing
- **Yellow:** Connecting to WiFi
- **Cyan:** WebSocket connected
- **Green:** Ready for input
- **Magenta:** Recording audio
- **Red:** Error state

## Key Technical Features

### PDM Microphone Configuration

The critical difference from MicroPython is the use of `I2S_MODE_PDM`:

```cpp
i2s_config_t i2s_config_mic = {
  .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX | I2S_MODE_PDM),
  .sample_rate = 24000,
  .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
  .channel_format = I2S_CHANNEL_FMT_ONLY_RIGHT,
  // ... additional configuration
};
```

This flag enables the ESP32's hardware PDM decoder, which is required for the SPM1423 PDM microphone.

### Audio Pipeline

1. **Recording:** Button press → i2s_read() from PDM mic → Base64 encode → WebSocket send
2. **Playback:** WebSocket receive → JSON parse → Base64 decode → i2s_write() → Speaker

### State Machine

The system uses a state machine to manage flow:
- `INIT` → `WIFI_CONNECTING` → `WIFI_CONNECTED` → `WS_CONNECTING` → `WS_CONNECTED` → `READY`
- `READY` → `RECORDING` (button pressed) → `READY` (audio sent)
- `READY` → `SPEAKING` (response received) → `READY` (playback done)
- Any state → `ERROR` (on failure)

## Troubleshooting

### Compilation Errors

- **"M5Atom.h: No such file"** → Install M5Atom library
- **"WebSocketsClient.h: No such file"** → Install WebSockets library
- **"ArduinoJson.h: No such file"** → Install ArduinoJson library

### Upload Fails

- Make sure COM port is correct (Tools → Port)
- Try pressing and holding the button while uploading
- Check USB cable (must support data, not just power)

### WiFi Connection Issues

- Verify SSID and password in `config.h`
- Check 2.4GHz WiFi (ESP32 doesn't support 5GHz)
- Monitor Serial output for connection errors

### Microphone Returns Zeros

- Verify PDM pins: CLK=GPIO33, DATA=GPIO23
- Check I2S_MODE_PDM flag is present in setupI2SMicrophone()
- Ensure M5Atom library is up to date

### No Audio Playback

- Verify speaker pins: BCK=GPIO19, WS=GPIO33, DATA=GPIO22
- Check I2S speaker setup in setupI2SSpeaker()
- Adjust volume (speaker is quite loud by default)

## Next Steps

- [ ] Test complete voice interaction flow
- [ ] Implement audio playback from OpenAI responses
- [ ] Optimize audio buffer sizes for latency
- [ ] Add LED animations for better status feedback
- [ ] Implement push-to-talk vs continuous recording toggle
- [ ] Add OTA firmware updates
- [ ] Power optimization for battery operation

## License

MIT License - See root LICENSE file

## References

- [M5Stack ATOM Echo Documentation](https://docs.m5stack.com/en/atom/atom_echo)
- [ESP-IDF I2S Driver](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/i2s.html)
- [OpenAI Realtime API](https://platform.openai.com/docs/guides/realtime)
