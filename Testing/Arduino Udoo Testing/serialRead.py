'''
This file is meant to run on the UDOO Bold and read sensor data from its Arduino over the built in serial port
'''

# Import necessary libraries
import serial
import time
import struct

# Open a serial connection
ser = serial.Serial('/dev/ttyACM0',9600,timeout=1)
ser.flushOutput()
print('Serial connected')

a = 0
v = 0

# Loop forever, reading two characters and printing them out
while True:
    r = ser.readline()[:-1]
    if r.strip():
        a,v = eval(r.decode("utf-8"))
    print(a,v)
    time.sleep(0.01)
