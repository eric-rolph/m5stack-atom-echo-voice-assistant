# ATOM Echo - PlatformIO + ESP-IDF

This is the **working solution** for PDM microphone support on the M5Stack ATOM Echo. It uses PlatformIO with the pure ESP-IDF framework, avoiding all Arduino library conflicts.

## Why ESP-IDF Instead of Arduino?

The Arduino framework on ESP32 has **fundamental I2S driver conflicts**:
- PDM microphones require ESP-IDF's new `i2s_driver` with `I2S_MODE_PDM`
- Arduino ecosystem libraries (M5Atom, FastLED, Adafruit NeoPixel) use the **legacy I2S driver**
- These two drivers are **mutually exclusive** at the ESP-IDF level
- Error: `E (373) i2s(legacy): CONFLICT! The new i2s driver can't work along with the legacy i2s driver`

See `../arduino/ARCHITECTURAL_BLOCKER.md` for full details.

## Features

✅ **PDM Microphone** - SPM1423 on GPIO 23 (DATA), GPIO 33 (CLK)  
✅ **I2S Speaker** - NS4168 amplifier on I2S1  
✅ **SK6812 LED** - RGB control via RMT peripheral (no I2S conflict!)  
✅ **Button** - GPIO 39 with debouncing  
✅ **WiFi** - Connects to configured network  
✅ **Microphone Test** - Press button to verify PDM mic works  

## Setup

### 1. Install PlatformIO

**Option A: VS Code Extension (Recommended)**
1. Install VS Code extension: `PlatformIO IDE`
2. Restart VS Code

**Option B: Command Line**
```powershell
pip install platformio
```

### 2. Configure WiFi (Already Done)

WiFi credentials are in `platformio.ini`:
```ini
-DCONFIG_ESP_WIFI_SSID=\"Everest\"
-DCONFIG_ESP_WIFI_PASSWORD=\"hillaryhellscape\"
```

### 3. Build and Upload

**VS Code:**
1. Open this folder in VS Code
2. Click "Build" in PlatformIO toolbar (checkmark icon)
3. Click "Upload" (right arrow icon)
4. Click "Serial Monitor" to view output

**Command Line:**
```powershell
cd platformio-espidf
pio run -t upload -t monitor
```

## Expected Output

```
=== ATOM Echo Voice Assistant ===
Build: PlatformIO + ESP-IDF
ESP-IDF Version: 5.x.x
Initializing SK6812 LED on GPIO 27
WiFi init complete, connecting to Everest
WiFi connected! IP: 192.168.x.x
Initializing PDM microphone...
PDM microphone initialized successfully!
Initializing I2S speaker...
I2S speaker initialized successfully!
Setup complete - Ready!
Testing PDM microphone...
Read 1024 samples (2048 bytes)
Non-zero samples: 987 / 1024 (96.4%)
Sample range: [-8192, 8191]
✓ PDM microphone is working!
```

## Hardware Pins

| Peripheral | Pin | Description |
|------------|-----|-------------|
| Button | GPIO 39 | Active low, internal pullup |
| LED | GPIO 27 | SK6812 RGB (WS2812 compatible) |
| PDM Mic CLK | GPIO 33 | SPM1423 clock |
| PDM Mic DATA | GPIO 23 | SPM1423 data |
| I2S Speaker BCK | GPIO 19 | NS4168 bit clock |
| I2S Speaker WS | GPIO 33 | NS4168 word select |
| I2S Speaker DATA | GPIO 22 | NS4168 audio data |

## LED Status

| Color | Status |
|-------|--------|
| Blue | Initializing |
| Yellow | WiFi connecting |
| Cyan | WiFi connected |
| Green | Ready |
| Magenta | Recording audio |
| Red | Error |

## Next Steps

1. ✅ **Verify PDM microphone works** - Press button, check for non-zero samples
2. Add WebSocket client using `esp_websocket_client`
3. Add Base64 encoding for audio data
4. Add JSON handling using `cJSON`
5. Integrate OpenAI Realtime API
6. Add audio playback to speaker

## Project Structure

```
platformio-espidf/
├── platformio.ini          # PlatformIO configuration
├── sdkconfig.defaults      # ESP-IDF configuration
├── partitions.csv          # Flash partition table
└── src/
    ├── main.c              # Main application
    ├── led_strip_encoder.h # LED control header
    ├── led_strip_encoder.c # LED control implementation
    └── ca_cert.pem         # SSL root certificate
```

## Troubleshooting

**Build errors:**
- Make sure PlatformIO is installed: `pio --version`
- Clean build: `pio run -t clean`

**Upload fails:**
- Check COM port in `platformio.ini` (currently COM9)
- Press and hold button while uploading if needed

**No serial output:**
- Check baud rate is 115200
- Try resetting device: `pio device monitor --eol LF`

**Microphone returns all zeros:**
- Check PDM pin connections (GPIO 23, 33)
- Verify SPM1423 is getting 3.3V power
- Check I2S configuration in `main.c`

## References

- [ESP-IDF I2S Driver](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/i2s.html)
- [ESP-IDF PDM Mode](https://github.com/espressif/esp-idf/tree/master/examples/peripherals/i2s/i2s_codec)
- [PlatformIO ESP32](https://docs.platformio.org/en/latest/platforms/espressif32.html)
- [M5Stack ATOM Echo Schematic](https://m5stack.oss-cn-shenzhen.aliyuncs.com/resource/docs/schematic/Core/ATOM_ECHO_ATOMIC_SCHEMATIC.pdf)
