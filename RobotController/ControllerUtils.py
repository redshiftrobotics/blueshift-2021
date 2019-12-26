simpleMode = False
try:
    import evdev
except:
    simpleMode = True

'''
import logging
'''

class DriveController():
    def __init__(self, order=[0,1,2,3,4,5,6,7], flip=[0,0,0,0,0,0,0,0]):
        self.settings = {
            "motor_order": {
                "frontLeft": order[0],
                "frontRight": order[1],
                "backLeft": order[2],
                "backRight": order[3],
                "verticalFrontLeft": order[4],
                "verticalFrontRight": order[5],
                "verticalBackLeft": order[6],
                "verticalBackRight": order[7]
            },
            "style": "holonomic",
            "motor_flip": flip
        }
        self.joyHorizontal = 0
        self.joyForward = 0
        self.joyRotation = 0
        self.joyVertical = 0
        self.mtrSpeeds = [0]*len(order)
    
    def updateState(self, event):
        code = event.code
        value = event.value
        
        if ((value <= -50 or value >= 50) and (code == 0 or code == 1 or code == 3 or code == 4) and event.type !=0):
            if code == 0:
                self.joyHorizontal = self.deadzoneCorrect(value)
            if code == 1:
                self.joyForward = self.deadzoneCorrect(value)
            if code == 3:
                self.joyRotation = self.deadzoneCorrect(value)
            if code == 4:
                self.joyVertical = self.deadzoneCorrect(value)

    def calcThrust(self, style="holonomic"):
        """ Calculates the speed for each motor based on stored controller inputs

            Returns:
                An array of calculated motors speed values
        """
        if self.settings["style"] == "holonomic":
            self.mtrSpeeds[self.settings["motor_order"]["frontLeft"]] = self.clamp(self.remapDeg(self.joyForward + self.joyHorizontal + self.joyRotation), 0, 180)
            self.mtrSpeeds[self.settings["motor_order"]["frontRight"]] = self.clamp(self.remapDeg(-self.joyForward + self.joyHorizontal + self.joyRotation), 0, 180)
            self.mtrSpeeds[self.settings["motor_order"]["backLeft"]] = self.clamp(self.remapDeg(self.joyForward - self.joyHorizontal + self.joyRotation), 0, 180)
            self.mtrSpeeds[self.settings["motor_order"]["backRight"]] = self.clamp(self.remapDeg(-self.joyForward - self.joyHorizontal + self.joyRotation), 0, 180)
            self.mtrSpeeds[self.settings["motor_order"]["verticalFrontLeft"]] = self.clamp(self.remapDeg(self.joyVertical), 0, 180)
            self.mtrSpeeds[self.settings["motor_order"]["verticalFrontRight"]] = self.clamp(self.remapDeg(self.joyVertical), 0, 180)
            self.mtrSpeeds[self.settings["motor_order"]["verticalBackLeft"]] = self.clamp(self.remapDeg(self.joyVertical), 0, 180)
            self.mtrSpeeds[self.settings["motor_order"]["verticalBackRight"]] = self.clamp(self.remapDeg(self.joyVertical), 0, 180)

        for i in range(len(self.mtrSpeeds)):
            if self.settings['motor_flip'][i]:
                self.mtrSpeeds[i] = 180-self.mtrSpeeds[i]
        return self.mtrSpeeds
    
    def calcPIDRot(self, x, y, z):
        if self.settings["style"] == "holonomic":
            self.mtrSpeeds[self.settings["motor_order"]["frontLeft"]] = self.clamp((z)*90 + 90, 0, 180)
            self.mtrSpeeds[self.settings["motor_order"]["frontRight"]] = self.clamp((z)*90 + 90, 0, 180)
            self.mtrSpeeds[self.settings["motor_order"]["backLeft"]] = self.clamp((z)*90 + 90, 0, 180)
            self.mtrSpeeds[self.settings["motor_order"]["backRight"]] = self.clamp((z)*90 + 90, 0, 180)
            self.mtrSpeeds[self.settings["motor_order"]["verticalFrontLeft"]] = self.clamp((x+y)*90 + 90, 0, 180)
            self.mtrSpeeds[self.settings["motor_order"]["verticalFrontRight"]] = self.clamp((-x+y)*90 + 90, 0, 180)
            self.mtrSpeeds[self.settings["motor_order"]["verticalBackLeft"]] = self.clamp((x-y)*90 + 90, 0, 180)
            self.mtrSpeeds[self.settings["motor_order"]["verticalBackRight"]] = self.clamp((-x-y)*90 + 90, 0, 180)
        for i in range(len(self.mtrSpeeds)):
            if self.settings['motor_flip'][i]:
                self.mtrSpeeds[i] = 180-self.mtrSpeeds[i]
        return self.mtrSpeeds
    
    def remapDeg(self, val):
        """ Remaps a controller input to servo range

            Arguments:
                val: value to remap

            Returns:
                The remapped value
        """
        deg = -val/32768.0 * 90.0 + 90.0
        return deg

    def clamp(self, n, minn, maxn):
        """ Clamps a number in a range

            Arguments:
                n: number to clamp
                minn: minimum value for n
                maxn: maximum value for n

            Returns:
                the clamped value
        """
        return max(min(maxn, n), minn)

    def deadzoneCorrect(self, val, deadzone_range=150):
        """ Corrects a value if it is in the controller's deadzone

            Argument:
                val: value to correct

            Returns:
                the corrected value
        """
        if deadzone_range > val > -deadzone_range:
            return 0
        else:
            return val

    def checkArrayValue(self, arry, val):
        """ Checks if each item in array is equal to an input value

            Arguments:
                arry: array to check
                val: value to check againts the array

            Returns:
                True if each item in the array was equal to the val
                Otherwise False
        """
        return all(item==val for item in arry)

    def zeroMotors(self):
        return [90]*len(self.mtrSpeeds)

def isStopCode(event):
    """ Checks if the input event is a stop code (Back Button)

        Arguments:
            event: gamepad event to check

        Returns:
            Whether the event is a stop code
    """
    return event.code == 314 and event.value == 1


def isZeroMotorCode(event):
    """ Checks if the input event is a zero motor code (X Button)

        Arguments:
            event: gamepad event to check

        Returns:
            Whether the event is a zero motor code
    """
    return event.code == 307 and event.value == 1

def isStabilizeCode(event):
    """ Checks if the input event is a stop code (A Button)

        Arguments:
            event: gamepad event to check

        Returns:
            Whether the event is a stabilize code
    """
    return event.code == 304 and event.value == 1

def isOverrideCode(event, action="down"):
    """ Checks if the input event is a stop code (B Button)

        Arguments:
            event: gamepad event to check

        Returns:
            Whether the event is an override code
    """
    actions = {
        "down": 1,
        "up": 0
    }
    return event.code == 305 and event.value == actions[action]

def identifyController():
        """ Searches the available devices for a controller and returns it

            Returns:
                A controller device if it can find any
        """
        if not simpleMode:
            controller_names = ["Logitech Gamepad F710", "Logitech Gamepad F310", "Microsoft X-Box One S pad", "PowerA Xbox One wired controller"]

            allDevices = [evdev.InputDevice(path) for path in evdev.list_devices()]
            controllerDevices = []
            
            for device in allDevices:
                for controllerName in controller_names:
                    if device.name == controllerName:
                        controllerDevices.append(device)
            
            if len(controllerDevices) > 0:
                return controllerDevices[0]
            else:
                raise Exception("Could not find valid controller device")
        else:
            return None