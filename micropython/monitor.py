"""Quick monitor script for ATOM Echo"""
import serial
import time

ser = serial.Serial('COM9', 115200, timeout=0.1)
time.sleep(1)

# Send Ctrl-C then Ctrl-D to reset
ser.write(b'\x03\x03')
time.sleep(0.3)
ser.write(b'\x04')
time.sleep(2)

# Run main
ser.write(b'import main\r\n')
time.sleep(1)

# Monitor output
print("Device output:\n" + "="*60)
try:
    while True:
        if ser.in_waiting:
            print(ser.read(ser.in_waiting).decode('utf-8', errors='ignore'), end='', flush=True)
        time.sleep(0.05)
except KeyboardInterrupt:
    print("\n" + "="*60)
    ser.close()
