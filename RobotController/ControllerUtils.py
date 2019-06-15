import evdev
import logging

# Number-Motor mappings
frontLeft = 0
frontRight = 1
backLeft = 2
backRight = 3
verticalLeft = 4
verticalRight = 5
verticalFront = 6
verticalBack = 7

# Values to store the controller inputs and motor speeds
joyForward = 0
joyHorizontal = 0
joyRotation = 0
joyVertical = 0
mtrSpeeds = [0,0,0,0,0,0]

def remapDeg(val):
    """ Remaps a controller input to servo range

        Arguments:
            val: value to remap

        Returns:
            The remapped value
    """
    deg = -val/32768.0 * 90.0 + 90.0
    return deg

def calcThrust():
    """ Calculates the speed for each motor based on stored controller inputs

        Returns:
            An array of calculated motors speed values
    """
    global joyForward
    global joyHorizontal
    global joyRotation
    global joyVertical

    mtrSpeeds[frontLeft] = 180-clamp(remapDeg(joyForward - joyHorizontal + joyRotation), 0, 180)
    mtrSpeeds[frontRight] = clamp(remapDeg(-joyForward + joyHorizontal + joyRotation), 0, 180)
    mtrSpeeds[backLeft] = 180-clamp(remapDeg(joyForward - joyHorizontal + joyRotation), 0, 180)
    mtrSpeeds[backRight] = clamp(remapDeg(-joyForward + joyHorizontal + joyRotation), 0, 180)
    mtrSpeeds[verticalLeft] = clamp(remapDeg(joyVertical), 0, 180)
    mtrSpeeds[verticalRight] = clamp(remapDeg(joyVertical), 0, 180)
    return mtrSpeeds

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

def deadzoneCorrect(val):
    """ Corrects a value if it is in the controller's deadzone

        Argument:
            val: value to correct

        Returns:
            the corrected value
    """
    if 150 > val > -150:
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
    return all(item==val for item in array)

def identifyControllers():
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
        logging.debug("Selecting first device: "+controllerDevices[0].name)
        return controllerDevices[0]
    else:
        logging.error("Could not find valid controller device")

def processEvent(generator):
    """ Processes a gamepad event and extracts relevant values

        Arguments:
            generator: the event to extract data from
    """
    global joyForward
    global joyHorizontal
    global joyRotation
    global joyVertical
    
    code = generator.code
    value = generator.value
    
    if ((value <= -50 or value >= 50) and (code == 0 or code == 1 or code == 3 or code == 4) and generator.type !=0):
        if code == 0:
            joyHorizontal = deadzoneCorrect(value)
        if code == 1:
            joyForward = deadzoneCorrect(value)
        if code == 3:
            joyRotation = deadzoneCorrect(value)
        if code == 4:
            joyVertical = deadzoneCorrect(value)

def isStopCode(event):
    """ Checks if the input event is a stop code

        Arguments:
            event: gamepad event to check

        Returns:
            Whether the event is a stop code
    """
    return event.code == 316 and event.value == 1