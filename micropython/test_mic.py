"""Test microphone directly"""
import machine
from machine import Pin, I2S
import time

# M5Stack ATOM Echo pinout
I2S_MIC_BCK = 19
I2S_MIC_WS = 33
I2S_MIC_DATA = 23

print("Initializing microphone...")
i2s_mic = I2S(
    1,
    sck=Pin(I2S_MIC_BCK),
    ws=Pin(I2S_MIC_WS),
    sd=Pin(I2S_MIC_DATA),
    mode=I2S.RX,
    bits=16,
    format=I2S.MONO,
    rate=24000,
    ibuf=20000
)

print("Microphone initialized")
print("Reading 10 samples...")

buffer = bytearray(9600)

for i in range(10):
    bytes_read = i2s_mic.readinto(buffer)
    print(f"Sample {i+1}: Read {bytes_read} bytes")
    if bytes_read > 0:
        # Print first few bytes as hex
        print(f"  First 16 bytes: {buffer[:16].hex()}")
    time.sleep(0.2)

print("Test complete")
