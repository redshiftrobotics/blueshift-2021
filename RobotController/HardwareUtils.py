simpleMode = False
try:
    # Import I2C Communication Libraries
    from board import SCL, SDA
    import busio
    from adafruit_motor import servo

    # Import the PCA9685 module (16 Motor 12 bit PWM Servo Driver)
    from adafruit_pca9685 import PCA9685

    # Import the BNO055 module (Absolute Orientation IMU Fusion Breakout)
    from adafruit_bno055 import BNO055
except:
    simpleMode = True
    from noise import pnoise1
    from random import randint
    import time

settings = {
    "servo_settings": {
        "T100": {
            "min_pulse": 1500,
            "max_pulse": 1900
        }
    }
}

if not simpleMode:
    i2c = busio.I2C(SCL, SDA)

class ServoDriver():
    def __init__(self, servo_locs,frequency=50):
        if not simpleMode:
            self.pca = PCA9685(i2c)
            self.pca.frequency = frequency
            self.servos = [None]*16
            for i,(loc,s_type) in enumerate(servo_locs):
                self.servos.append((servo.Servo(pca.channels[loc],
                                            settings["servo_settings"][s_type]["min_pulse"],
                                            settings["servo_settings"][s_type]["max_pulse"]),s_type))
    def set_servo(self, loc,speed):
        if not simpleMode:
            if self.servos[loc]:
                self.servos[loc][0].angle = speed
            else:
                raise Exception("There is no servo at {}".format(loc))

    def set_all_servos(self, loc, speed, only_type=False):
        if not simpleMode:
            for servo,s_type in self.servos:
                if servo and (only_type == False or s_type == only_type):
                    servo.angle = speed
    
    def shutdown(self):
        if not simpleMode:
            self.pca.deinit()

class IMUFusion():
    def __init__(self):
        if not simpleMode:
            self.imu = BNO055(i2c)
        else:
            self.offsets = {
                "imu": {
                    "calibration": {
                        "sys": randint(0, 1000),
                        "gyro": randint(0, 1000),
                        "accel": randint(0, 1000),
                        "mag": randint(0, 1000)
                    },
                    "gyro": {
                        "x": randint(0, 1000),
                        "y": randint(0, 1000),
                        "z": randint(0, 1000),
                    },
                    "linAccel": {
                        "x": randint(0, 1000),
                        "y": randint(0, 1000),
                        "z": randint(0, 1000),
                    }
                },
                "temp": randint(0, 1000)
            }
            self.start = time.time()
            self.octaves = 2
    
    def get_full_state(self):
        state = {
            "imu": {
                "calibration": {
                    "sys": 0,
                    "gyro": 0,
                    "accel": 0,
                    "mag": 0
                },
                "gyro": {
                    "x": 0,
                    "y": 0,
                    "z": 0,
                },
                "linAccel": {
                    "x": 0,
                    "y": 0,
                    "z": 0,
                }
            },
            "temp": 0
        }

        if not simpleMode:
            gyro = self.imu.euler
            lin_accel = self.imu.linear_acceleration
            temp = self.imu.temperature
            calibration = self.imu.calibration_status

            state["imu"]["calibration"]["sys"] = calibration[0]
            state["imu"]["calibration"]["gyro"] = calibration[1]
            state["imu"]["calibration"]["accel"] = calibration[2]
            state["imu"]["calibration"]["mag"] = calibration[3]
            
            state["imu"]["gyro"]["x"] = gyro[0]
            state["imu"]["gyro"]["y"] = gyro[1]
            state["imu"]["gyro"]["z"] = gyro[2]

            state["imu"]["linAccel"]["x"] = lin_accel[0]
            state["imu"]["linAccel"]["y"] = lin_accel[1]
            state["imu"]["linAccel"]["z"] = lin_accel[2]
            
            state["temp"] = temp
        else:
            x = float(-(time.time()-self.start))/150.0

            state["imu"]["calibration"]["sys"] = (pnoise1(x+self.offsets["imu"]["calibration"]["sys"], self.octaves))*2+2
            state["imu"]["calibration"]["gyro"] = (pnoise1(x+self.offsets["imu"]["calibration"]["gyro"], self.octaves))*2+2
            state["imu"]["calibration"]["accel"] = (pnoise1(x+self.offsets["imu"]["calibration"]["accel"], self.octaves))*2+2
            state["imu"]["calibration"]["mag"] = (pnoise1(x+self.offsets["imu"]["calibration"]["mag"], self.octaves))*2+2
            
            state["imu"]["gyro"]["x"] = pnoise1(x+self.offsets["imu"]["gyro"]["x"], self.octaves)*180
            state["imu"]["gyro"]["y"] = pnoise1(x+self.offsets["imu"]["gyro"]["y"], self.octaves)*180
            state["imu"]["gyro"]["z"] = pnoise1(x+self.offsets["imu"]["gyro"]["z"], self.octaves)*180

            state["imu"]["linAccel"]["x"] = pnoise1(x+self.offsets["imu"]["linAccel"]["x"], self.octaves)*60
            state["imu"]["linAccel"]["y"] = pnoise1(x+self.offsets["imu"]["linAccel"]["y"], self.octaves)*60
            state["imu"]["linAccel"]["z"] = pnoise1(x+self.offsets["imu"]["linAccel"]["z"], self.octaves)*60
            
            state["temp"] = pnoise1(x+self.offsets["temp"], self.octaves)*5+21
        
        return state
    
