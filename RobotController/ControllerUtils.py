import evdev
import logging

class DriveController():
    def __init__(self, order=[0,1,2,3,4,5,6,7]):
        self.settings = {
            "motor_order": {
                "frontLeft": order[0],
                "frontRight": order[1],
                "backLeft": order[2],
                "backRight": order[3],
                "verticalLeft": order[4],
                "verticalRight": order[5],
                "verticalFront": order[6],
                "verticalBack": order[7]
            },
            "style": "holonomic"
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
                self.joyHorizontal = deadzoneCorrect(value)
            if code == 1:
                self.joyForward = deadzoneCorrect(value)
            if code == 3:
                self.joyRotation = deadzoneCorrect(value)
            if code == 4:
                self.joyVertical = deadzoneCorrect(value)

    def calcThrust(self, style="holonomic"):
        """ Calculates the speed for each motor based on stored controller inputs

            Returns:
                An array of calculated motors speed values
        """
        if settings["style"] == "holonomic":
            self.mtrSpeeds[settings["motor_order"]["frontLeft"]] = 180-self.clamp(self.remapDeg(self.joyForward - self.joyHorizontal + self.joyRotation), 0, 180)
            self.mtrSpeeds[settings["motor_order"]["frontRight"]] = self.clamp(self.remapDeg(-self.joyForward + self.joyHorizontal + self.joyRotation), 0, 180)
            self.mtrSpeeds[settings["motor_order"]["backLeft"]] = 180-self.clamp(self.remapDeg(self.joyForward - self.joyHorizontal + self.joyRotation), 0, 180)
            self.mtrSpeeds[settings["motor_order"]["backRight"]] = self.clamp(self.remapDeg(-self.joyForward + self.joyHorizontal + self.joyRotation), 0, 180)
            self.mtrSpeeds[settings["motor_order"]["verticalLeft"]] = self.clamp(self.remapDeg(self.joyVertical), 0, 180)
            self.mtrSpeeds[settings["motor_order"]["verticalRight"]] = self.clamp(self.remapDeg(self.joyVertical), 0, 180)
            self.mtrSpeeds[settings["motor_order"]["verticalFront"]] = self.clamp(self.remapDeg(self.joyVertical), 0, 180)
            self.mtrSpeeds[settings["motor_order"]["verticalBack"]] = self.clamp(self.remapDeg(self.joyVertical), 0, 180)
        return self.mtrSpeeds
    
    def remapDeg(val):
        """ Remaps a controller input to servo range

            Arguments:
                val: value to remap

            Returns:
                The remapped value
        """
        deg = -val/32768.0 * 90.0 + 90.0
        return deg

    def clamp(n, minn, maxn):
        """ Clamps a number in a range

            Arguments:
                n: number to clamp
                minn: minimum value for n
                maxn: maximum value for n

            Returns:
                the clamped value
        """
        return max(min(maxn, n), minn)

    def deadzoneCorrect(val,deadzone_range=150):
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

    def checkArrayValue(arry,val):
        """ Checks if each item in array is equal to an input value

            Arguments:
                arry: array to check
                val: value to check againts the array

            Returns:
                True if each item in the array was equal to the val
                Otherwise False
        """
        return all(item==val for item in arry)

def isStopCode(event):
    """ Checks if the input event is a stop code

        Arguments:
            event: gamepad event to check

        Returns:
            Whether the event is a stop code
    """
    return event.code == 316 and event.value == 1


def isZeroMotorCode(event):
    """ Checks if the input event is a stop code

        Arguments:
            event: gamepad event to check

        Returns:
            Whether the event is a stop code
    """
    return event.code == 304 and event.value == 1

def identifyController():
        """ Searches the available devices for a controller and returns it

            Returns:
                A controller device if it can find any
        """
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