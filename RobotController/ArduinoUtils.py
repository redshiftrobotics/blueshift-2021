import serial
from time import sleep

def earthSensorThread(run, out):
    ser = serial.Serial('/dev/ttyACM0',9600,timeout=1)
    ser.flushOutput()

    while run:
        r = ser.readline()[:-1]
        if r.strip():
            a,v = eval(r.decode("utf-8"))
            out = {
                "amps": a,
                "volts": v
            }

        sleep(1/30.0)