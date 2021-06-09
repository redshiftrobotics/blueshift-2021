'''
This file has both the Air and Earth nodes
'''
# Utility Imports
import sys
import os
import argparse

# Stores if the program is in testing mode or not
simpleMode = False

# Check if the program is in testing mode and enable it if so 
parser = argparse.ArgumentParser()
parser.add_argument("-s", "--simple", help="""Run the program in simple mode (fake data and no special libraries).
                    Useful for running on any device other than the robot""",
                    action="store_true")
args = parser.parse_args()

simpleMode = args.simple

# TODO: Bring back the logging system
# Imports for Logging
import logging
#from pythonjsonlogger import jsonlogger

# Imports for Threading
import threading
from queue import Queue, LifoQueue
from copy import copy

# Imports for Video Streaming
sys.path.insert(0, 'imagezmq/imagezmq')
import cv2
import imagezmq
import numpy as np

# Imports for Communication
import socket
import CommunicationUtils
import simplejson as json
import time
# TODO: Migrate this to the Jetson for V2
#import ArduinoUtils

# Imports for Controller Communication and Processing
import ControllerUtils
from simple_pid import PID



# Imports for AirNode
from flask import Flask, render_template, Response
from flask_socketio import SocketIO

EARTH_IP_WLAN = '0.0.0.0'

# Imports for Computer Vision
import ComputerVisionUtils

# Settings Dict to keep track of editable settings for data processing
settings = {
    "numCams": 3,
    "maxCams": 3,
    "drive": "holonomic",
    "numMotors": 8,
    "minMotorSpeed": 0,
    "maxMotorSpeed": 180,
    "camStreamSleep": 1.0/30.0
}

# Dict to stop threads
execute = {
    "streamVideo": True,
    "receiveData": True,
    "sendData": True,
    "mainThread": True
}

# Queues to send data to specific Threads
airQueue = Queue(0)
airCamQueues = {
    "mainCam": LifoQueue(0),
    "bkpCam1": LifoQueue(0),
    "bkpCam2": LifoQueue(0),
    "cvCam": LifoQueue(0)
}

recvDataQueue = Queue(0)
sendDataQueue = Queue(0)
recvImageQueue = Queue(0)
mainQueue = Queue(0)

# TODO: Move this to a more central location
# Maybe make a communication manager that handles sending and recieving messages through queues and sockets

# Dict that stores message tags and the threads the go to
tags = {
    "sensor": [airQueue, mainQueue],
    "cam": {
        "mainCam": [airCamQueues["mainCam"],mainQueue],
        "bkpCam1": [airCamQueues["bkpCam1"]],
        "bkpCam2": [airCamQueues["bkpCam2"]],
        },
    "motorData": [sendDataQueue, airQueue],
    "log": [airQueue],
    "stateChange": [airQueue, recvDataQueue, sendDataQueue, recvImageQueue, mainQueue],
    "settingChange": [mainQueue, sendDataQueue]
}

def stopAllThreads(callback=0):
    """ Stops all currently running threads
        
        Argument:
            callback: (optional) callback event
    """

    execute['streamVideo'] = False
    execute['receiveData'] = False
    execute['sendData'] = False
    execute['mainThread'] = False

    if callable(callback):
        callback()

def handlePacket(qData, debug=False):
    """ Handles communication between all of the other threads

        Arguments:
            debug: (optional) log debugging data
    """

    # Figure out where a packet should be sent based on its tag, and put it in the correct queue(s)
    if qData['tag'] in tags:
        if qData['tag'] ==  "cam":
            for threadQueue in tags[qData['tag']][qData['metadata']]:
                CommunicationUtils.clearQueue(threadQueue)
                threadQueue.put(qData)
        else:
            for threadQueue in tags[qData['tag']]:
                threadQueue.put(qData)

def mainThread(debug=False):
    """ Controls the robot including joystick input, computer vision, line following, etc.

        Arguments:
            debug: (optional) log debugging data
    """

    # Initialize a drive controller object to hande generating motor values
    DC = ControllerUtils.DriveController(flip=[1,0,1,0,0,0,1,0])

    # Select a controller object
    gamepad = None
    while (not gamepad) and execute['mainThread']:
        time.sleep(5)
        try:
            gamepad = ControllerUtils.Joystick(1)
        except Exception as e:
            print(e)


    # Create empty objects to store sensor and image data
    newestImage = np.array([])
    newestSensorState = {
        'imu': {
            'calibration': {
                'sys': 0, 
                'gyro': 0, 
                'accel': 0, 
                'mag': 0
            }, 
            'gyro': {
                'x': 0, 
                'y': 0, 
                'z': 0
            },
            'vel': {
                'x': 0,
                'y': 0,
                'z': 0
            }
        },
        'temp': 25
    }

    # Initalize PID Rotation controllers
    rot = {
        "Kp": 1,
        "Kd": 0.1,
        "Ki": 0.05
    }
    xRotPID = PID(rot["Kp"], rot["Kd"], rot["Ki"], setpoint=0)
    yRotPID = PID(rot["Kp"], rot["Kd"], rot["Ki"], setpoint=0)
    zRotPID = PID(rot["Kp"], rot["Kd"], rot["Ki"], setpoint=0)

    # Store the target rotation
    stabilizeRot = {
        "x": 0,
        "y": 0,
        "z": 0
    }

    # Initalize PID Position controllers
    pos = {
        "Kp": 1,
        "Kd": 0.1,
        "Ki": 0.05
    }
    xPosPID = PID(pos["Kp"], pos["Kd"], pos["Ki"], setpoint=0)
    yPosPID = PID(pos["Kp"], pos["Kd"], pos["Ki"], setpoint=0)
    zPosPID = PID(pos["Kp"], pos["Kd"], pos["Ki"], setpoint=0)

    # Stores the current and previous modes
    mode = "user-control"
    override = False
    lastMode = "user-control"
    lastOverride = False

    # Stores the currently running CV debug level
    lineFollowingDebugLevel = "Mask"

    # Store the result of coral reef analysis
    coralReefOutPath = "static/assets/coralHealth/"
    coralReefDone = False
    coralReefReference = 'static/assets/coralHealth/coral_old.png'

    # Create an empty array to store computer vision data
    cvImage = np.array([])
    
    # This is the fastest speed that the loop should run at in seconds
    loopFrequency = 1.0/25.0
    lastLoop = time.time()

    # This is the main control loop
    while execute['mainThread']:
        # Read all the messages in our queue
        while not mainQueue.empty():
            recvMsg = mainQueue.get()

            if recvMsg['tag'] == 'cam':
                # Update the camera array
                newestImage = CommunicationUtils.decodeImage(recvMsg['data'])
            elif recvMsg['tag'] == 'sensor':
                # Update the sensor dict
                newestSensorState = recvMsg['data']
            elif recvMsg['tag'] == 'stateChange':
                if recvMsg['metadata'] == "stop-motors":
                    # Send a stop motor signal
                    handlePacket(CommunicationUtils.packet("motorData", DC.zeroMotors(), metadata="drivetrain"))
                    # Set the mode to user control
                    mode = "user-control"
                elif recvMsg['metadata'] == "follow-line":
                    if recvMsg['data'] == "run":
                        # Enable follow line mode
                        mode = "follow-line-init"
                elif recvMsg['metadata']== "coral-recieve-image":
                     coralReefReference = recvMsg['data']

                elif recvMsg['metadata'] == "analyze-coral-reef":
                    if recvMsg['data'] == "run":
                        # If there is camera data, run coral reef analysis
                        print(recvMsg)
                        if newestImage.size > 0:
                            analyzeCoralReefThread = threading.Thread(target=ComputerVisionUtils.findCoralHealth, args=(copy(newestImage), coralReefOutPath, coralReefReference, coralReefDone,), daemon=True)
                            analyzeCoralReefThread.start()
                        else:
                            # TODO: handle the [noCamera] command in the correct places
                            handlePacket(CommunicationUtils.packet(tag="stateChange", data="noCamera", metadata="analyze-coral-reef"))
                
                elif recvMsg['metadata'] == "stabilize":
                    # Set the correct rotation target
                    stabilizeRot["x"] = recvMsg["data"]["x"]
                    stabilizeRot["y"] = recvMsg["data"]["y"]
                    stabilizeRot["z"] = recvMsg["data"]["z"]
                    # Set the mode to initialize stabilization
                    mode = "stabilize-init"
                elif recvMsg['metadata'] == "hold-angle":
                    # Set the rotation target
                    stabilizeRot["x"] = recvMsg["data"]["x"]
                    stabilizeRot["y"] = recvMsg["data"]["y"]
                    stabilizeRot["z"] = recvMsg["data"]["z"]
                    # Set the mode to initialize holding the current angle
                    mode = "hold-angle-init"
            elif recvMsg['tag'] == 'settingChange':
                if recvMsg['metadata'] == "follow-line":
                    # Set the computer vision debugging algorithm and data
                    lineFollowingDebugLevel = recvMsg['data']
        
        override = False

        # Setup the gamepad mapping
        # TODO: Create "side" classes so we don't need to use dictionaries
        gamepadMapping = {
            "x-mov": gamepad.left["stick"]["x"],
            "y-mov": gamepad.left["stick"]["y"],
            "z-mov": -gamepad.left["bumper"]+gamepad.right["bumper"],
            "x-rot": gamepad.right["stick"]["x"],
            "y-rot": gamepad.right["stick"]["y"],
            "z-rot": -gamepad.left["trigger"]+gamepad.right["trigger"]
        }

        # Set mode based on gamepad state
        if (gamepad.left["stick"]["button"] and gamepad.right["stick"]["button"]): # Enable Override
            override = True
        elif (gamepad.buttons["back"]):
            # Shutdown the program
            handlePacket(CommunicationUtils.packet("stateChange", "close"))
            time.sleep(1)
            stopAllThreads()
        elif (gamepad.buttons["x"]):
            # Activate user-control mode and stop motors
            handlePacket(CommunicationUtils.packet("motorData", DC.zeroMotors(), metadata="drivetrain"))
            mode = "user-control"
        elif (gamepad.buttons["y"]):
            # Activate stabilize mode
            if (mode != "stabilize" and mode != "stabilize-init"):
                # Zero the rotation target
                stabilizeRot["x"] = 0
                stabilizeRot["y"] = 0
                stabilizeRot["z"] = 0
                # Set the mode to initialize stabilization
                mode = "stabilize-init"

        # Run the selected mode
        # If override is on, we want to ignore the selected mode and give user full control
        if (not override):
            if (mode == "stabilize-init"): # Initialize stabilize mode
                # Reset PID rotation controllers
                xRotPID.reset()
                yRotPID.reset()
                zRotPID.reset()
                xRotPID.tunings = (rot["Kp"], rot["Kd"], rot["Ki"])
                yRotPID.tunings = (rot["Kp"], rot["Kd"], rot["Ki"])
                zRotPID.tunings = (rot["Kp"], rot["Kd"], rot["Ki"])

                # Assuming the robot has been correctly calibrated, (0,0,0) should be upright
                xRotPID.setpoint = stabilizeRot["x"]
                yRotPID.setpoint = stabilizeRot["y"]
                zRotPID.setpoint = stabilizeRot["z"]
                # Set the mode to stabilize
                mode = "stabilize"
            elif (mode == "stabilize"):
                # Run stabilize mode

                # Get rotation values from the PID controllers
                xTgt = xRotPID(newestSensorState["imu"]["gyro"]["x"])
                yTgt = yRotPID(newestSensorState["imu"]["gyro"]["y"])
                zTgt = zRotPID(newestSensorState["imu"]["gyro"]["z"])

                # Use the rotation values to generate motor speeds
                speeds = DC.calcMotorValues(0, 0, 0, xTgt, yTgt, zTgt)

                # Create and send the motor speeds packet
                handlePacket(CommunicationUtils.packet("motorData", speeds, metadata="drivetrain"))
            elif (mode == "follow-line-init"): 
                # Initialize line following mode
                if newestImage.size > 0:
                    # Reset PID rotation controllers
                    xRotPID.reset()
                    yRotPID.reset()
                    zRotPID.reset()
                    xRotPID.tunings = (rot["Kp"], rot["Kd"], rot["Ki"])
                    yRotPID.tunings = (rot["Kp"], rot["Kd"], rot["Ki"])
                    zRotPID.tunings = (rot["Kp"], rot["Kd"], rot["Ki"])

                    # Assuming the robot has been correctly calibrated, (0,90,0) should be pointed at the ground
                    xRotPID.setpoint = 0
                    yRotPID.setpoint = 90
                    zRotPID.setpoint = 0

                    # Reset PID rotation controllers
                    xPosPID.reset()
                    xPosPID.tunings = (pos["Kp"], pos["Kd"], pos["Ki"])
                    xPosPID.setpoint = newestImage.shape[0]*ComputerVisionUtils.lf_percent_of_image_blue_lines_should_fill
                    # Enable follow line mode
                    mode = "follow-line"
                else:
                    # If we don't have camera data streaming, send a message, and revert to user control mode
                    handlePacket(CommunicationUtils.packet(tag="stateChange", data="noCamera", metadata="follow-line"))
                    mode = "user-control"
            elif (mode == "follow-line"):
                # Run line following mode
                
                # We only want to run the computer vision if we have a valid image
                if newestImage.size > 0:
                    cvOut = ComputerVisionUtils.detectLines(newestImage, cvOutLevel=lineFollowingDebugLevel)
                    if cvOut:
                        dist, angle, cvImage = cvOut
                        
                        # Rotation around the x axis aligns to the line
                        xRotTgt = xRotPID(angle)

                        # Rotation around the Y and Z axes keep the robot upright
                        yRotTgt = yRotPID(newestSensorState["imu"]["gyro"]["y"])
                        zRotTgt = zRotPID(newestSensorState["imu"]["gyro"]["z"])

                        # Movement on the x axis keeps a specific distance from the line
                        xPosTgt = xPosPID(dist)

                        # Calculate motor speeds
                        speeds = DC.calcMotorValues(xPosTgt, 0, 1, xRotTgt, yRotTgt, zRotTgt)

                        # Calculate motor speeds
                        handlePacket(CommunicationUtils.packet("motorData", speeds, metadata="drivetrain"))

                        # Send the CV Debug image
                        imgPacket = CommunicationUtils.packet(tag="cam", data=CommunicationUtils.encodeImage(cvImage), metadata="cvCam")
                        handlePacket(imgPacket)
                    else:
                        # If the line following failed, send a message
                        handlePacket(CommunicationUtils.packet(tag="stateChange", data="failed", metadata="follow-line"))
            elif (mode == "hold-angle-init"): # Initialize hold angle mode
                # Reset PID rotation controllers
                xRotPID.reset()
                yRotPID.reset()
                zRotPID.reset()
                xRotPID.tunings = (rot["Kp"], rot["Kd"], rot["Ki"])
                yRotPID.tunings = (rot["Kp"], rot["Kd"], rot["Ki"])
                zRotPID.tunings = (rot["Kp"], rot["Kd"], rot["Ki"])

                # Assuming the robot has been correctly calibrated, (0,0,0) should be upright
                xRotPID.setpoint = stabilizeRot["x"]
                yRotPID.setpoint = stabilizeRot["y"]
                zRotPID.setpoint = stabilizeRot["z"]
                mode = "hold-angle"
            elif (mode == "hold-angle"): # Run hold angle mode
                # Update the PID controllers
                xTgt = xRotPID(newestSensorState["imu"]["gyro"]["x"])
                yTgt = yRotPID(newestSensorState["imu"]["gyro"]["y"])
                zTgt = zRotPID(newestSensorState["imu"]["gyro"]["z"])

                # Calculate new motor values
                speeds = DC.calcMotorValues(gamepadMapping["x-mov"],
                                            gamepadMapping["y-mov"],
                                            gamepadMapping["z-mov"],
                                            xTgt,
                                            yTgt,
                                            zTgt)
                # Create and send the motor speeds packet
                handlePacket(CommunicationUtils.packet("motorData", speeds, metadata="drivetrain"))
        if (mode == "user-control" or override): # Run user control mode
            # Calculate new motor values
            speeds = DC.calcMotorValues(gamepadMapping["x-mov"],
                                        gamepadMapping["y-mov"],
                                        gamepadMapping["z-mov"],
                                        gamepadMapping["x-rot"],
                                        gamepadMapping["y-rot"],
                                        gamepadMapping["z-rot"])
                                        
            armDirection = gamepad.buttons['a'] - gamepad.buttons['b']

            armMovement = 0.1*armDirection
            
            # Create and send the motor speeds packet
            handlePacket(CommunicationUtils.packet("motorData", speeds, metadata="drivetrain"))
        
            handlePacket(CommunicationUtils.packet("gripData", armMovement, metadata="arm-angle"))

        
        # Handle coral reef algorthim
        if coralReefDone:
            # TODO: Add this to the website
            # Send a message when the coral reef algorithm is done
            handlePacket(CommunicationUtils.packet(tag="stateChange", data="done", metadata="analyze-coral-reef"))

        # Update the mode and override state that the AirNode displays
        # * Stabilization is a special case because one mode in code is used to represent two robot modes
        # * If the target angle is anything other than, the robot is in "rotate-to-angle" mode
        if (stabilizeRot["x"] != 0 and
            stabilizeRot["x"] != 0 and
            stabilizeRot["x"] != 0 and
            mode == "stabilize"): # Check if the target angle is not 0,0,0
                handlePacket(CommunicationUtils.packet(tag="stateChange", data="rotate-to-angle", metadata="mode"))
                lastMode = "rotate-to-angle"
        elif (mode != lastMode):
            handlePacket(CommunicationUtils.packet(tag="stateChange", data=mode, metadata="mode"))
            lastMode = mode
        
        # Send a message if we are in the override mode
        if (override != lastOverride):
            handlePacket(CommunicationUtils.packet(tag="stateChange", data=override, metadata="override"))
            lastOverride = override

        # TODO: Maybe make a custom sleep class to handle these timed loops
        # Sleep to control the loop speed
        timeDiff = time.time()-lastLoop
        if loopFrequency-timeDiff > 0:
            time.sleep(loopFrequency-timeDiff)

        now = time.time()
        handlePacket(CommunicationUtils.packet(tag="stateChange", data=1/(now-lastLoop), metadata="earth-fps"))
        lastLoop = now

def receiveVideoStreams(debug=False):
    """ Recieves and processes video from the Water Node then sends it to the Air Node
    
        Arguments:
            debug: (optional) log debugging data
    """

	# Initialize the ZMQ server
    image_hub = imagezmq.ImageHub(open_port='tcp://*:'+str(CommunicationUtils.CAM_PORT))
    while execute['streamVideo']:
        image_b64 = ""
        imgInfo = ""
        if not simpleMode:
            # Read and store an encoded jpg image
            imgInfo, image_b64 = image_hub.recv_jpg()
        else:
            # Read and encode an image
            imgInfo, image_raw = image_hub.recv_image()
            image_b64 = CommunicationUtils.encodeImage(image_raw)

        # Separate the timestamp from the device name
        deviceName, timestamp = imgInfo.split("|")

        # Let the clent know we got the image
        image_hub.send_reply(b'OK')
        
        # Create and send the image packet
        imgPacket = CommunicationUtils.packet(tag="cam", data=image_b64, timestamp=timestamp, metadata=deviceName, copy_data=False)
        handlePacket(imgPacket)

def receiveData(debug=False):
    """ Recieves and processes JSON data from the Water Node

        Arguments:
            debug: (optional) log debugging data
    """

    # Setup arduino communication
    arduinoData = {
        "amps": 0,
        "volts": 0
    }
    # arduinoThread = threading.Thread(target=ArduinoUtils.earthSensorThread, args=(execute['receiveData'], arduinoData,))
    # arduinoThread.start()

    # Get the IP address and port of the earth node
    HOST = CommunicationUtils.SIMPLE_EARTH_IP if simpleMode else CommunicationUtils.EARTH_IP
    PORT = CommunicationUtils.SNSR_PORT

    # Create the socket connection
    snsr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    snsr.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    snsr.bind((HOST, PORT))
    # Listen and accept connections
    snsr.listen()
    conn, addr = snsr.accept()

    while execute['receiveData']:
        # Recieve and handle messages
        recvPacket = CommunicationUtils.recvMsg(conn)
        
        # Add EarthNode sensor data to the WaterNode sensor data
        if recvPacket['tag'] == "sensor":
            recvPacket["amps"] = arduinoData["amps"]
            recvPacket["volts"] = arduinoData["volts"]
        
        handlePacket(recvPacket)
    
    # Close the connection
    conn.close()
    snsr.close()

    # Close arduino communication
    # arduinoThread.join()

def sendData(debug=False):
    """ Sends JSON data to the Water Node

        Arguments:
            debug: (optional) log debugging data
    """

    # Get the IP address and port of the earth node
    HOST = CommunicationUtils.SIMPLE_EARTH_IP if simpleMode else CommunicationUtils.EARTH_IP
    PORT = CommunicationUtils.CNTLR_PORT

    # Create the socket connection
    cntlr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cntlr.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    cntlr.bind((HOST, PORT))
    # Listen and accept connections
    cntlr.listen()
    conn, addr = cntlr.accept()

    while execute['sendData']:
        while not sendDataQueue.empty():
            # Get and send all of our queued messages
            sendPacket = sendDataQueue.get()
            CommunicationUtils.sendMsg(conn, sendPacket)
    
    # Close the connection
    conn.close()
    cntlr.close()

def startAirNode(debug=False):
    # Initialize Flask
    app = Flask(__name__)

    # Disable Logging
    log = logging.getLogger('werkzeug')
    log.disabled = True
    app.logger.disabled = True

    # Initialize SocketIO
    socketio = SocketIO(app)

    @app.route('/pilot')
    def left():
        return render_template('pilot.html')

    @app.route('/copilot')
    def copilot():
        return render_template('copilot.html')

    @app.route('/cv')
    def right():
        return render_template('cv.html')

    def messageReceived(methods=['GET', 'POST']):
        print('message was received!!!')

    @socketio.on('getAirNodeUpdates')
    def getAir(recv, methods=["GET","POST"]):
        # Send queued messages to the airNode on its request
        while not airQueue.empty():
            tosend = airQueue.get()

            # TODO: Add this check globally
            # and take into account whether a message is high priority or not

            # We only send messages that are newer than 0.1 seconds
            # This only works assuming that ALL of the data being sent is in streams
            # Such as sensor or camera data
            if (tosend['timestamp'] - time.time() < 0.1):
                socketio.emit("updateAirNode", tosend)
    
    @socketio.on('sendUpdate')
    def getUpdate(recv, methods=["GET","POST"]):
        # Handle messages from the airNode
        handlePacket(recv)
        
    # Handle streaming all of the different cameras
    def camGen(camName):
        camQueue = airCamQueues[camName]
        while True:
            # test = camQueue.get()
            # print(time.time() - test['timestamp'])
            # tosend = (b'--frame\r\n'+b'Content-Type: image/jpeg\r\n\r\n' + test['data'] + b'\r\n\r\n')
            
            tosend = (b'--frame\r\n'+b'Content-Type: image/jpeg\r\n\r\n' + camQueue.get()['data'] + b'\r\n\r\n')
            '''
            if debug:
                logger.debug("Sending new image to Air Node")
            '''
            yield tosend

    @app.route('/videoFeed/<camName>')
    def videoFeed(camName):
        return Response(camGen(camName), mimetype='multipart/x-mixed-replace; boundary=frame')

    # TODO: Improve mode system with a development, deployment, simple mode, etc.
    
    # Setup auto reload of files for easy development 
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    socketio.run(app,host=EARTH_IP_WLAN, port=CommunicationUtils.AIR_PORT, debug=False)



if( __name__ == "__main__"):
    # Setup Logging preferences
    verbose = [False,True]

	# Start all of the threads for communication
    mainThread = threading.Thread(target=mainThread, args=(verbose[0],))
    vidStreamThread = threading.Thread(target=receiveVideoStreams, args=(verbose[0],))
    recvDataThread = threading.Thread(target=receiveData, args=(verbose[0],))
    sendDataThread = threading.Thread(target=sendData, args=(verbose[0],))
    airNodeThread = threading.Thread(target=startAirNode, args=(verbose[0],))
    mainThread.start()
    vidStreamThread.start()
    recvDataThread.start()
    sendDataThread.start()
    airNodeThread.start()

	# We don't want the program to end uptil all of the threads are stopped
    while execute['streamVideo'] or execute['receiveData'] or execute['sendData'] or execute['mainThread']:
        time.sleep(0.1)
    mainThread.join()
    recvDataThread.join()
    sendDataThread.join()
    vidStreamThread.join()
    airNodeThread.join()
    '''
    logger.debug("Stopped all Threads")
    logger.info("Shutting Down Ground Node")
    '''

    # TODO: Actually make this clear ALL of the queues, not just the air node
    # Clear all queues
    CommunicationUtils.clearQueue(airQueue)