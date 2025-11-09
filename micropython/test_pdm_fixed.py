"""
Test PDM microphone with correct I2S PDM mode
Based on M5Stack ATOM Echo RecordPlay example
"""
from machine import I2S, Pin
import array

# PDM Microphone pins (from M5Stack docs)
PDM_CLK_PIN = 33   # Clock to microphone
PDM_DATA_PIN = 23  # Data from microphone

print("Initializing I2S in PDM RX mode...")

# Configure I2S for PDM microphone input
# Key: Use I2S.RX mode - this enables PDM decoding in ESP-IDF
i2s = I2S(
    0,  # I2S peripheral 0
    sck=Pin(19),      # Not used for PDM, but required by MicroPython
    ws=Pin(PDM_CLK_PIN),   # PDM Clock
    sd=Pin(PDM_DATA_PIN),  # PDM Data
    mode=I2S.RX,           # RECEIVE mode enables PDM!
    bits=16,
    format=I2S.MONO,
    rate=16000,
    ibuf=20000
)

print("I2S initialized. Recording 1 second of audio...")

# Read audio samples
samples = bytearray(32000)  # 1 second at 16kHz, 16-bit
num_read = i2s.readinto(samples)

print(f"Read {num_read} bytes")

# Convert to 16-bit samples and check values
sample_array = array.array('h', samples)
print(f"\nFirst 10 samples: {sample_array[:10]}")
print(f"Max sample: {max(sample_array)}")
print(f"Min sample: {min(sample_array)}")

# Check if we got real audio (non-zero values)
non_zero = sum(1 for s in sample_array if s != 0)
print(f"Non-zero samples: {non_zero} out of {len(sample_array)} ({100*non_zero/len(sample_array):.1f}%)")

if non_zero > len(sample_array) * 0.5:
    print("\n✅ SUCCESS! PDM microphone is working!")
else:
    print("\n❌ Still getting zeros. PDM may need additional configuration.")

i2s.deinit()
