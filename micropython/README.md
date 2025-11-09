# M5Stack ATOM Echo - Standalone OpenAI Voice Assistant

A completely standalone voice assistant running on the M5Stack ATOM Echo that talks **directly** to OpenAI's API over HTTPS. No PC, no Raspberry Pi, no backend server required.

## Hardware

- **Device**: M5Stack ATOM Echo (ESP32-PICO-D4)
- **Features**: Built-in microphone, speaker, RGB LED, button

## Requirements

### Firmware
- **MicroPython** for ESP32 with:
  - I2S support (for audio input/output)
  - SSL/TLS support (for HTTPS to OpenAI)
  - urequests library

Recommended build: MicroPython v1.20+ for ESP32 with I2S

### APIs
- OpenAI API key with access to:
  - Whisper (speech-to-text)
  - GPT-4 or GPT-3.5 (chat)
  - TTS (text-to-speech)

## Setup

### 1. Flash MicroPython

Download and flash a MicroPython firmware with I2S support to your ATOM Echo:

```bash
esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash
esptool.py --chip esp32 --port /dev/ttyUSB0 write_flash -z 0x1000 micropython-esp32.bin
```

### 2. Configure

Edit `config.py` with your credentials:

```python
WIFI_SSID = "YourWiFiName"
WIFI_PSK = "YourWiFiPassword"
OPENAI_API_KEY = "sk-..."
```

### 3. Upload Files

Upload both files to the ATOM Echo:

```bash
ampy --port /dev/ttyUSB0 put config.py
ampy --port /dev/ttyUSB0 put main.py
```

Or use Thonny IDE, rshell, or mpremote.

### 4. Run

Reset the device or run:

```python
import main
```

## Usage

1. **Green LED**: Device is ready
2. **Press button**: Start recording
3. **Yellow LED**: Recording (3 seconds)
4. **Blue LED**: Sending to OpenAI
5. **Cyan LED**: Processing AI response
6. **Magenta LED**: Playing audio response
7. **Green LED**: Ready for next interaction

## How It Works

### Voice Interaction Flow

```
Button Press
    ↓
Record Audio (3s)
    ↓
Send to OpenAI Whisper API → Get Transcript
    ↓
Send Transcript to ChatGPT API → Get AI Response
    ↓
Send AI Text to TTS API → Get Audio
    ↓
Play Audio on Speaker
    ↓
Ready for Next Interaction
```

### Pin Configuration

**DO NOT MODIFY** - These are hardware-specific M5Stack ATOM Echo pins:

```python
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
```

## Architecture

This is a **true standalone solution**:

- ✅ ESP32 hardware (M5Stack ATOM Echo)
- ✅ Direct HTTPS calls to api.openai.com
- ✅ All processing happens in the cloud
- ✅ No PC/server/proxy required
- ✅ Only needs WiFi and OpenAI API key

## Troubleshooting

### SSL Certificate Errors

If you get SSL/TLS errors, your MicroPython build may not include proper CA certificates. You can:

1. Use a newer MicroPython build with SSL support
2. Modify `urequests` calls to disable verification (not recommended for production)

### Memory Issues

The ESP32 has limited RAM. If you run out of memory:

- Reduce `RECORDING_MS` in config.py (shorter recordings)
- Reduce `max_tokens` in chat API call
- Call `gc.collect()` more frequently

### Audio Quality

- Recording is 16kHz, 16-bit, mono PCM
- Adjust `RECORDING_MS` for longer/shorter clips
- OpenAI TTS returns 24kHz PCM by default
- If audio sounds wrong, check I2S pin connections

### No Sound

1. Verify speaker pins are correct (BCK=19, WS=33, DATA=22)
2. Check volume - ATOM Echo speaker is small
3. Ensure TTS response format is "pcm" not "mp3"

### Button Not Working

- Button is active-low with internal pull-up
- Pin 39 is input-only on ESP32
- Check button wiring if using breakout

## API Costs

Approximate OpenAI API costs per interaction:

- Whisper: $0.006 per minute ($0.0003 for 3s)
- GPT-4o-mini: $0.00015 per 1K tokens (~$0.0003 per interaction)
- TTS: $0.015 per 1M characters (~$0.0001 per interaction)

**Total: ~$0.0007 per voice interaction**

## License

MIT License - feel free to modify and use

## Credits

- M5Stack for ATOM Echo hardware
- OpenAI for Whisper, GPT, and TTS APIs
- MicroPython project for ESP32 support
