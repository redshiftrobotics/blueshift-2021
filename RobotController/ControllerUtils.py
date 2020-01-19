simpleMode = False
try:
    import evdev
except:
    simpleMode = True

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
        self.mtrSpeeds = [0]*len(order)

    def calcMotorValues(self, xm, ym, zm, xr, yr, zr):
        """ Calculates the speed for each motor 6 inputs, each representing a degree of freedom

            Returns:
                An array of calculated motors speed values
        """
        if self.settings["style"] == "holonomic":
            self.mtrSpeeds[self.settings["motor_order"]["frontLeft"]] = self.clamp((xm+ym+zr), -1, 1)
            self.mtrSpeeds[self.settings["motor_order"]["frontRight"]] = self.clamp((-xm+ym+zr), -1, 1)
            self.mtrSpeeds[self.settings["motor_order"]["backLeft"]] = self.clamp((xm-ym+zr), -1, 1)
            self.mtrSpeeds[self.settings["motor_order"]["backRight"]] = self.clamp((-xm-ym+zr), -1, 1)
            self.mtrSpeeds[self.settings["motor_order"]["verticalFrontLeft"]] = self.clamp((zm+xr+yr), -1, 1)
            self.mtrSpeeds[self.settings["motor_order"]["verticalFrontRight"]] = self.clamp((zm-xr+yr), -1, 1)
            self.mtrSpeeds[self.settings["motor_order"]["verticalBackLeft"]] = self.clamp((zm+xr-yr), -1, 1)
            self.mtrSpeeds[self.settings["motor_order"]["verticalBackRight"]] = self.clamp((zm-xr-yr), -1, 1)
        
        for i in range(len(self.mtrSpeeds)):
            if self.settings['motor_flip'][i]:
                self.mtrSpeeds[i] = -1 * self.mtrSpeeds[i]
        return self.mtrSpeeds
    
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

    def zeroMotors(self):
        return [0]*len(self.mtrSpeeds)

def updateGamepadState(gamepadOut, device, stop):
    """ Updates the state of a gamepad object to based on evdev events

        Arguments:
            gamepadOut: gamepad object to update
            device: evdev device to read updates from 
            stop: reference to variable that can stop the loop
    """
    stickScale = 32768.0
    triggerScale = 255.0
    for event in device.read_loop():
        if not stop:
            break
        if event.type !=0:
            code = event.code
            value = event.value

            if code == 0:
                gamepadOut.left["stick"]["x"] = -value/stickScale
            elif code == 1:
                gamepadOut.left["stick"]["y"] = value/stickScale
            elif code == 3:
                gamepadOut.right["stick"]["x"] = value/stickScale
            elif code == 4:
                gamepadOut.right["stick"]["y"] = -value/stickScale
            elif code == 2:
                gamepadOut.left["trigger"] = value/triggerScale
            elif code == 5:
                gamepadOut.right["trigger"] = value/triggerScale
            elif code == 16:
                if value == -1:
                    gamepadOut.d_pad["left"] = 1
                    gamepadOut.d_pad["right"] = 0
                elif value == 1:
                    gamepadOut.d_pad["left"] = 0
                    gamepadOut.d_pad["right"] = 1
                else:
                    gamepadOut.d_pad["left"] = 0
                    gamepadOut.d_pad["right"] = 0
            elif code == 17:
                if value == -1:
                    gamepadOut.d_pad["up"] = 1
                    gamepadOut.d_pad["down"] = 0
                elif value == 1:
                    gamepadOut.d_pad["up"] = 0
                    gamepadOut.d_pad["down"] = 1
                else:
                    gamepadOut.d_pad["up"] = 0
                    gamepadOut.d_pad["down"] = 0
            elif code == 304:
                if value == 1:
                    gamepadOut.buttons["a"] = 1
                else:
                    gamepadOut.buttons["a"] = 0
            elif code == 305:
                if value == 1:
                    gamepadOut.buttons["b"] = 1
                else:
                    gamepadOut.buttons["b"] = 0
            elif code == 307:
                if value == 1:
                    gamepadOut.buttons["x"] = 1
                else:
                    gamepadOut.buttons["x"] = 0
            elif code == 308:
                if value == 1:
                    gamepadOut.buttons["y"] = 1
                else:
                    gamepadOut.buttons["y"] = 0
            elif code == 310:
                if value == 1:
                    gamepadOut.left["bumper"] = 1
                else:
                    gamepadOut.left["bumper"] = 0
            elif code == 311:
                if value == 1:
                    gamepadOut.right["bumper"] = 1
                else:
                    gamepadOut.right["bumper"] = 0
            elif code == 317:
                if value == 1:
                    gamepadOut.left["stick"]["button"] = 1
                else:
                    gamepadOut.left["stick"]["button"] = 0
            elif code == 318:
                if value == 1:
                    gamepadOut.right["stick"]["button"] = 1
                else:
                    gamepadOut.right["stick"]["button"] = 0

class Gamepad:
    def __init__(self):
        self.left = {
            "stick": {
                "x": 0,
                "y": 0,
                "button": 0
            },
            "bumper": 0,
            "trigger": 0
        }
        self.right = {
            "stick": {
                "x": 0,
                "y": 0,
                "button": 0
            },
            "bumper": 0,
            "trigger": 0
        }
        self.d_pad = {
            "up": 0,
            "down": 0,
            "left": 0,
            "right": 0
        }
        self.buttons = {
            "back": 0,
            "start": 0,
            "home": 0,
            "a": 0,
            "b": 0,
            "x": 0,
            "y": 0
        }

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