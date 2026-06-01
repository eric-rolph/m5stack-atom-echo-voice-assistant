# M5Stack ATOM Echo Voice Assistant (Direct-to-OpenAI Bare-Metal)

A highly optimized, bare-metal OpenAI Realtime voice assistant built specifically for the [M5Stack ATOM Echo](https://docs.m5stack.com/en/atom/atomecho).

## Why this project is unique

While several other popular ESP32 voice assistant projects rely on intermediate servers or frameworks, this project takes a **pure bare-metal, direct-connection** approach:

*   **No Proxies or Edge Servers:** Unlike projects like `FabrikappAgency/esp32-realtime-voice-assistant` (which uses a custom Node.js/LangChain server proxy) or `akdeb/ElatoAI` (which relies on Deno Edge / Cloudflare workers), this firmware connects **directly to the OpenAI Realtime API via Secure WebSockets**.
*   **Pure ESP-IDF (No Arduino or ESPHome):** Unlike `fjfricke/ha-openai-realtime` (which relies on ESPHome connecting to a Home Assistant WebSocket server) or ElatoAI (Arduino framework), this is a pure ESP-IDF C application. This allows for deep hardware and memory optimization.
*   **Extreme Memory Optimization:** The ATOM Echo features a tiny 320KB internal RAM without external PSRAM. This firmware is hyper-optimized to decode large Base64 audio chunks directly into I2S DMA buffers without triggering heap fragmentation or TLS memory exhaustion.
*   **Shared I2S/PDM Pin Wrangling:** The ATOM Echo shares a single pin (`GPIO33`) for both the PDM microphone clock and the I2S speaker word-select. This project implements seamless, real-time driver multiplexing to switch between listening and speaking modes on the fly.

This makes the repository an excellent reference for anyone looking to build independent, serverless voice agents on severely resource-constrained IoT devices.

## Features
- Real-time audio streaming (24kHz PCM16) via Secure WebSockets directly to the OpenAI Realtime API (`gpt-realtime-mini`).
- Low-latency voice activation and continuous listening.
- Advanced jitter and buffer underrun protection.
- Audio output playback via the internal NS4168 I2S speaker.
- Simple Wi-Fi connectivity and automatic TLS reconnection.

## Hardware Support
This project is configured specifically for the **M5Stack ATOM Echo** smart speaker:
- Microphone: SPM1423 PDM Mic (CLK: GPIO33, DAT: GPIO23)
- Speaker: NS4168 I2S Amp (BCK: GPIO19, WS: GPIO33, DAT: GPIO22)
- Wi-Fi/Bluetooth: ESP32-PICO-D4 (240MHz, 320KB SRAM)

## Usage
1. Provide your Wi-Fi credentials and OpenAI API Key in `main.c`.
2. Build and flash the firmware using ESP-IDF v5.5+.
3. Once booted, the device will connect to Wi-Fi and directly to the OpenAI WebSocket.
4. The assistant will proactively greet you. Start speaking naturally!
