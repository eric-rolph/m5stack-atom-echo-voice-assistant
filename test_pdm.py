import serial
import time

ser = serial.Serial('COM9', 115200, timeout=5)
time.sleep(1)

# Send commands to test PDM
commands = [
    b'import audiobusio\r\n',
    b'import board\r\n',
    b'mic = audiobusio.PDMIn(board.PDM_MIC_CLK, board.PDM_MIC_DATA, sample_rate=16000, bit_depth=16)\r\n',
    b'print("PDM mic initialized!")\r\n',
    b'import array\r\n',
    b'samples = array.array("H", [0] * 160)\r\n',
    b'mic.record(samples, len(samples))\r\n',
    b'print("Sample:", samples[0], samples[1], samples[2])\r\n',
]

for cmd in commands:
    ser.write(cmd)
    time.sleep(0.5)

time.sleep(2)
output = ser.read(8192).decode('utf-8', errors='replace')
print(output)
ser.close()
