'''
This is a script to test reading data from an IMU using our custom class
'''

# Import necessary libraries
import sys
# Because the .py file with our custom class is in another folder, we need to add that folder to our path
sys.path.append('../../RobotController')

import HardwareUtils
import time

# Initialize the IMU
IMU = HardwareUtils.IMUFusion()

# Read data forever
while 1:
    IMU.get_full_state()
    time.sleep(1.0/1.0)