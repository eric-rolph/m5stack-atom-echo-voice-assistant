"""
M5Stack ATOM Echo - OpenAI Realtime API Configuration Template
Copy this file to config_realtime.py and fill in your actual credentials
"""

# WiFi Credentials
WIFI_SSID = "your_wifi_ssid_here"
WIFI_PSK = "your_wifi_password_here"

# OpenAI API Configuration
# Get your API key from: https://platform.openai.com/api-keys
OPENAI_API_KEY = "sk-proj-your-openai-api-key-here"

# Realtime API Settings
REALTIME_MODEL = "gpt-4o-realtime-preview-2024-10-01"  # or gpt-4o-mini-realtime-preview
REALTIME_URL = f"wss://api.openai.com/v1/realtime?model={REALTIME_MODEL}"

# Audio Settings - Must match OpenAI Realtime API requirements
SAMPLE_RATE = 24000  # 24 kHz required by Realtime API
BITS_PER_SAMPLE = 16
CHANNELS = 1  # Mono

# Device Configuration
BUTTON_PIN = 39
NEOPIXEL_PIN = 27
NEOPIXEL_COUNT = 1

# I2S Speaker Configuration (NS4168 Amplifier)
I2S_SPEAKER_BCK = 19
I2S_SPEAKER_WS = 33
I2S_SPEAKER_DATA = 22

# PDM Microphone Configuration (SPM1423)
# Note: MicroPython I2S driver does not support PDM mode
# This project requires Arduino/ESP-IDF for PDM microphone support
PDM_MIC_CLK = 33
PDM_MIC_DATA = 23

# Network Settings
WIFI_TIMEOUT = 15  # seconds
MAX_WIFI_RETRIES = 3
WEBSOCKET_PING_INTERVAL = 30  # seconds

# Debug Settings
DEBUG = True
PRINT_AUDIO_STATS = False
