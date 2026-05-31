# M5Stack ATOM Echo Voice Assistant

This repository contains the ESP-IDF C application for turning the M5Stack ATOM Echo into an OpenAI Realtime Voice Assistant.

## Features
- Real-time audio streaming (24kHz PCM16) via WebSockets to the OpenAI Realtime API (`gpt-realtime-mini`).
- Low-latency voice activation and continuous listening.
- Audio output playback via the internal NS4168 I2S speaker.
- Simple Wi-Fi connectivity and automatic reconnection.

## Hardware Support
This project is configured specifically for the **M5Stack ATOM Echo** smart speaker:
- Microphone: SPM1423 PDM Mic (CLK: GPIO33, DAT: GPIO23)
- Speaker: NS4168 I2S Amp (BCK: GPIO19, WS: GPIO33, DAT: GPIO22)
- Wi-Fi/Bluetooth: ESP32-PICO-D4 (240MHz)

*Note: The speaker and microphone share GPIO33. The firmware seamlessly handles switching between input and output modes.*

## Usage
1. Provide your Wi-Fi credentials and OpenAI API Key in `main.c`.
2. Build and flash the firmware using ESP-IDF v5.5+.
3. Once booted, the device will connect to Wi-Fi and the OpenAI WebSocket.
4. The assistant will proactively greet you. Start speaking naturally!
