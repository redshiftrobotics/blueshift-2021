import sys
sys.path.append('../../RobotController')

import HardwareUtils
import time

IMU = HardwareUtils.IMUFusion()

while 1:
    IMU.get_full_state()
    time.sleep(1.0/1.0)