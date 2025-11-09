# M5Stack ATOM Echo Pin Configuration

## Official M5Stack Pin Map

Based on M5Stack documentation (https://docs.m5stack.com/en/atom/atomecho):

| Function | GPIO | Description |
|----------|------|-------------|
| **Button** | 39 | User button with internal pull-up |
| **LED** | 27 | SK6812 RGB LED (WS2812 protocol) |
| **Microphone (SPM1423)** | 23 (DATA) | PDM digital microphone |
| | 33 (CLK) | PDM clock signal |
| **Speaker (NS4168)** | 22 (DATA) | I2S audio data |
| | 19 (BCLK) | I2S bit clock |
| | 33 (LRCK/WS) | I2S word select |

## Important Notes

### GPIO 33 Dual Usage
**GPIO 33 is shared between the microphone PDM clock and speaker I2S word select.** This is intentional in the M5Stack design and documented in their specification.

⚠️ **Warning from M5Stack:** "G19 / G22 / G23 / G33 have been predefined. Do not reuse these pins; otherwise the Atom Echo may be damaged"

### How This Works
- **PDM Microphone Mode:** When the I2S peripheral is configured in PDM RX mode, GPIO 33 acts as the PDM clock
- **I2S Speaker Mode:** When the I2S peripheral is configured in standard TX mode, GPIO 33 acts as the word select (LRCLK)
- **Time-Division:** The firmware switches between microphone and speaker modes as needed - they don't operate simultaneously

### ESP32 I2S Peripheral Configuration

#### Microphone (PDM RX Mode)
```c
i2s_config_t mic_config = {
    .mode = I2S_MODE_MASTER | I2S_MODE_RX | I2S_MODE_PDM,
    .sample_rate = 16000,  // or 24000
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_ALL_RIGHT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    // ... other settings
};

i2s_pin_config_t mic_pins = {
    .bck_io_num = 19,      // Not used in PDM mode but must be set
    .ws_io_num = 33,       // PDM CLK
    .data_out_num = -1,    // Not used for RX
    .data_in_num = 23      // PDM DATA
};
```

#### Speaker (Standard I2S TX Mode)
```c
i2s_config_t spk_config = {
    .mode = I2S_MODE_MASTER | I2S_MODE_TX,
    .sample_rate = 16000,  // or 24000, 44100, 88200
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_RIGHT,
    .communication_format = I2S_COMM_FORMAT_I2S,
    // ... other settings
};

i2s_pin_config_t spk_pins = {
    .bck_io_num = 19,      // I2S BCLK
    .ws_io_num = 33,       // I2S LRCK/WS
    .data_out_num = 22,    // I2S DATA
    .data_in_num = -1      // Not used for TX
};
```

## Hardware Specifications

### ESP32-PICO-D4
- **CPU:** 240MHz dual-core Xtensa LX6
- **Flash:** 4MB
- **RAM:** 320KB
- **WiFi:** 802.11 b/g/n
- **Bluetooth:** BT/BLE 4.2

### SPM1423 PDM Microphone
- **Type:** Digital PDM MEMS microphone
- **Frequency Range:** 100Hz - 10kHz
- **Sensitivity:** -26dBFS
- **SNR:** 64dB

### NS4168 I2S Amplifier
- **Type:** Class D audio amplifier
- **Output Power:** 0.8W @ 4Ω
- **THD+N:** <1% @ 0.5W
- **Interface:** I2S standard mode

### SK6812 RGB LED
- **Type:** Addressable RGB LED
- **Protocol:** WS2812/WS2811 compatible
- **Control:** RMT peripheral (GPIO 27)
- **Colors:** 24-bit RGB (8-bit per channel)

## Code Implementation Status

### Current Pin Definitions (main.c)
```c
#define BUTTON_PIN      39
#define LED_PIN         27
#define PDM_MIC_CLK     33
#define PDM_MIC_DATA    23
#define I2S_SPK_BCK     19
#define I2S_SPK_WS      33
#define I2S_SPK_DATA    22
```

✅ **These pin assignments are correct** and match the official M5Stack specification.

### Initialization Sequence
1. **LED:** Initialize RGB LED via RMT peripheral (blue = initializing)
2. **WiFi:** Connect to network (yellow = connecting, cyan = connected)
3. **PDM Microphone:** Configure I2S in PDM RX mode at 24kHz
4. **I2S Speaker:** Configure I2S in standard TX mode at 24kHz
5. **Button Task:** Monitor GPIO 39 for button presses (magenta LED when pressed)

### Testing
- **Button Test:** Press button to see magenta LED and trigger microphone test
- **Microphone Test:** Reads 1024 samples and checks for non-zero data (indicates working microphone)
- **Speaker Test:** (Not yet implemented - needs test tone generator)

## References
- [M5Stack ATOM Echo Documentation](https://docs.m5stack.com/en/atom/atomecho)
- [ESP32 I2S Driver Documentation](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/i2s.html)
- [M5Atom GitHub Examples](https://github.com/m5stack/M5Atom/tree/main/examples/Echo)
