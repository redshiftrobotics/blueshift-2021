from HardwareUtils import ServoDriver
import time

sd = ServoDriver([(15, "T100")])

sd.set_servo(15, 0)
print("Initializing ESC...")
time.sleep(7)
print("Initialization finished. Sending commands")
sd.set_servo(15, 1)
time.sleep(7)

sd.shutdown()