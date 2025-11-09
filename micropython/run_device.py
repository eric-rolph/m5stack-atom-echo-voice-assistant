"""
Helper script to reset the ATOM Echo and run the main program
"""
import serial
import time

port = 'COM9'
baud = 115200

print(f"Connecting to {port}...")
ser = serial.Serial(port, baud, timeout=1)
time.sleep(0.5)

# Send Ctrl-C to interrupt any running program
print("Stopping any running program...")
ser.write(b'\x03')
time.sleep(0.2)

# Send Ctrl-D to soft reset
print("Soft resetting device...")
ser.write(b'\x04')
time.sleep(1)

# Wait for boot
print("Waiting for boot...")
time.sleep(2)

# Import and run main
print("Running main.py...")
ser.write(b'import main\r\n')
time.sleep(0.5)

# Read output for 10 seconds
print("\n" + "="*60)
print("Device Output:")
print("="*60)
start = time.time()
while time.time() - start < 10:
    if ser.in_waiting:
        data = ser.read(ser.in_waiting)
        try:
            print(data.decode('utf-8', errors='ignore'), end='')
        except:
            pass
    time.sleep(0.1)

print("\n" + "="*60)
print("\nDevice is running! Press the button to test voice interaction.")
print("The LED should be GREEN when ready.")
print("Press Ctrl+C to exit this monitor.")
print("="*60 + "\n")

# Continue reading
try:
    while True:
        if ser.in_waiting:
            data = ser.read(ser.in_waiting)
            try:
                print(data.decode('utf-8', errors='ignore'), end='')
            except:
                pass
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\n\nExiting...")
    ser.close()
