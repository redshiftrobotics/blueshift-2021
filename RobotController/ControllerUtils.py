import evdev
import logging

frontLeft = 0
frontRight = 1
backLeft = 2
backRight = 3
verticalLeft = 4
verticalRight = 5
verticalFront = 6
verticalBack = 7

# Create values to store the controller inputs
joyForward = 0
joyHorizontal = 0
joyRotation = 0
joyVertical = 0

mtrSpeeds = [0,0,0,0,0,0]

def remapDeg(val):
    deg = -val/32768.0 * 90.0 + 90.0
    return deg

def calcThrust():
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
    return max(min(maxn, n), minn)

def deadzoneCorrect(val):
    if 150 > val > -150:
        return 0
    else:
        return val

def checkCenter(array):
    return all(item==90 for item in array)

def identifyControllers():
    controller_names = ["Logitech Gamepad F710", "Logitech Gamepad F310", "Microsoft X-Box One S pad", "PowerA Xbox One wired controller"]

    allDevices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    logging.debug(allDevices)
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