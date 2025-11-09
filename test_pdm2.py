import serial
import time

ser = serial.Serial('COM9', 115200, timeout=5)
time.sleep(1)

# Send Ctrl-C to interrupt any running code
ser.write(b'\x03')
time.sleep(0.5)

# Send Ctrl-D to enter raw REPL mode
ser.write(b'\x04')
time.sleep(0.5)

# Read and discard the raw REPL prompt
ser.read(1000)

# Test PDM in raw REPL mode
test_code = b"""
import audiobusio
import board
import array

mic = audiobusio.PDMIn(board.PDM_MIC_CLK, board.PDM_MIC_DATA, sample_rate=16000, bit_depth=16)
print("PDM mic initialized successfully!")

samples = array.array("H", [0] * 160)
mic.record(samples, len(samples))
print(f"Sample values: {samples[0]}, {samples[1]}, {samples[2]}, {samples[3]}, {samples[4]}")
print(f"Max sample: {max(samples)}, Min sample: {min(samples)}")
"""

ser.write(test_code)
ser.write(b'\x04')  # Execute
time.sleep(2)

output = ser.read(8192).decode('utf-8', errors='replace')
print(output)
ser.close()
