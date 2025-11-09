"""Test microphone with different I2S formats"""
import machine
from machine import Pin, I2S
import time

# M5Stack ATOM Echo pinout
I2S_MIC_BCK = 19
I2S_MIC_WS = 33
I2S_MIC_DATA = 23

print("Testing different I2S configurations...")

# Test 1: Standard MONO
print("\n=== Test 1: MONO format ===")
try:
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
    buffer = bytearray(9600)
    bytes_read = i2s_mic.readinto(buffer)
    print(f"Read {bytes_read} bytes")
    print(f"First 32 bytes: {buffer[:32].hex()}")
    non_zero = sum(1 for b in buffer if b != 0)
    print(f"Non-zero bytes: {non_zero} / {bytes_read}")
    i2s_mic.deinit()
except Exception as e:
    print(f"Error: {e}")

# Test 2: STEREO format
print("\n=== Test 2: STEREO format ===")
try:
    i2s_mic = I2S(
        1,
        sck=Pin(I2S_MIC_BCK),
        ws=Pin(I2S_MIC_WS),
        sd=Pin(I2S_MIC_DATA),
        mode=I2S.RX,
        bits=16,
        format=I2S.STEREO,
        rate=24000,
        ibuf=20000
    )
    buffer = bytearray(9600)
    bytes_read = i2s_mic.readinto(buffer)
    print(f"Read {bytes_read} bytes")
    print(f"First 32 bytes: {buffer[:32].hex()}")
    non_zero = sum(1 for b in buffer if b != 0)
    print(f"Non-zero bytes: {non_zero} / {bytes_read}")
    i2s_mic.deinit()
except Exception as e:
    print(f"Error: {e}")

# Test 3: Different bit depth
print("\n=== Test 3: 32-bit ===")
try:
    i2s_mic = I2S(
        1,
        sck=Pin(I2S_MIC_BCK),
        ws=Pin(I2S_MIC_WS),
        sd=Pin(I2S_MIC_DATA),
        mode=I2S.RX,
        bits=32,
        format=I2S.MONO,
        rate=24000,
        ibuf=20000
    )
    buffer = bytearray(9600)
    bytes_read = i2s_mic.readinto(buffer)
    print(f"Read {bytes_read} bytes")
    print(f"First 32 bytes: {buffer[:32].hex()}")
    non_zero = sum(1 for b in buffer if b != 0)
    print(f"Non-zero bytes: {non_zero} / {bytes_read}")
    i2s_mic.deinit()
except Exception as e:
    print(f"Error: {e}")

print("\nTest complete")
