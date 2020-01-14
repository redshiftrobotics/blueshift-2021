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

# Imports for Logging
import logging
#from pythonjsonlogger import jsonlogger

# Imports for Threading
import threading
from queue import Queue

# Imports for Video Streaming
sys.path.insert(0, 'imagezmq/imagezmq')
import cv2
import imagezmq
import numpy as np

# Imports for Socket Communication
import socket
import CommunicationUtils
import simplejson as json
import time

# Imports for Controller Communication and Processing
import ControllerUtils
from simple_pid import PID

if not simpleMode:
    import evdev

# Imports for AirNode
from flask import Flask, render_template, Response
from flask_socketio import SocketIO

# Imports for finding the ip address of the wifi interface
import netifaces as ni
from netifaces import AF_INET

EARTH_IP_WLAN = 'localhost'
try:
    EARTH_IP_WLAN = ni.ifaddresses('wlp3s0')[AF_INET][0]['addr']
except:
    pass

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
    "mainCam": Queue(0),
    "bkpCam1": Queue(0),
    "bkpCam2": Queue(0),
    "cvCam": Queue(0)
}
recvDataQueue = Queue(0)
sendDataQueue = Queue(0)
recvImageQueue = Queue(0)
mainQueue = Queue(0)

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
    if qData['tag'] in tags:
        if qData['tag'] ==  "cam":
            for threadQueue in tags[qData['tag']][qData['metadata']]:
                threadQueue.put(qData)
        else:
            for threadQueue in tags[qData['tag']]:
                threadQueue.put(qData)

def mainThread(debug=False):
    """ Controls the robot including joystick input, computer vision, line following, etc.

        Arguments:
            debug: (optional) log debugging data
    """

    DC = ControllerUtils.DriveController(flip=[1,0,1,0,0,0,0,0])

    # Get Controller
    dev = None
    while (not dev) and execute['mainThread']:
        time.sleep(5)
        try:
            dev = ControllerUtils.identifyController()
        except Exception as e:
            print(e)
    
    gamepad = ControllerUtils.Gamepad()
    
    updateGamepadStateThreads = threading.Thread(target=ControllerUtils.updateGamepadState, args=(gamepad, dev, execute['mainThread'],), daemon=True)
    updateGamepadStateThreads.start()

    newestImage = []
    newestImageRaw = ""
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

    mode = "user-control"

    cvDebugAlgorithm = "cam"
    cvDebugLevel = "final"

    lastMsgTime = time.time()
    minTime = 1.0/10.0
    while execute['mainThread']:
        while not mainQueue.empty():
            recvMsg = mainQueue.get()
            if recvMsg['tag'] == 'cam':
                #newestImage = CommunicationUtils.decodeImage(recvMsg['data'])
                newestImageRaw = recvMsg['data']
            elif recvMsg['tag'] == 'sensor':
                newestSensorState = recvMsg['data']
            elif recvMsg['tag'] == 'stateChange':
                if recvMsg['metadata'] == "followLine":
                    mode = "follow-line-init"
                elif recvMsg['metadata'] == "stabilize":
                    stabilizeRot = recvMsg["data"]
                    mode = "stabilize-init"
            elif recvMsg['tag'] == 'settingChange':
                if recvMsg['metadata'] == "transectLine":
                    cvDebugAlgorithm = "transectLine"
                    cvDebugLevel = recvMsg['data']
                elif recvMsg['metadata'] == "coralHealth":
                    cvDebugAlgorithm = "coralHealth"
                    cvDebugLevel = recvMsg['data']
        
        override = False

        if (gamepad.left["stick"]["button"] and gamepad.right["stick"]["button"]): # Enable Override
            override = True
        elif (gamepad.buttons["back"]): # Stop the program
            handlePacket(CommunicationUtils.packet("stateChange", "close"))
            time.sleep(1)
            stopAllThreads()
        elif (gamepad.buttons["x"]): # Activate user-control mode and stop motors
            handlePacket(CommunicationUtils.packet("motorData", DC.zeroMotors(), metadata="drivetrain"))
            mode = "user-control"
        elif (gamepad.buttons["y"]): # Activate stabilize mode
            if (mode != "stabilize" and mode != "stabilize-init"):
                mode = "stabilize-init"
        
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
                mode = "stabilize"
            elif (mode == "stabilize"): # Run stabilize mode
                xTgt = xRotPID(newestSensorState["imu"]["gyro"]["x"])
                yTgt = yRotPID(newestSensorState["imu"]["gyro"]["y"])
                zTgt = zRotPID(newestSensorState["imu"]["gyro"]["z"])
                speeds = DC.calcMotorValues(0, 0, 0, xTgt, yTgt, zTgt)
                if (time.time() - lastMsgTime > minTime):
                    handlePacket(CommunicationUtils.packet("motorData", speeds, metadata="drivetrain"))
                    lastMsgTime = time.time()
            elif (mode == "follow-line-init"): # Initialize line following mode
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
                if newestImage:
                    xPosPID.setpoint = newestImage.shape[0]*ComputerVisionUtils.lf_percent_of_image_blue_lines_should_fill
                    mode = "follow-line"
                else:
                    handlePacket(CommunicationUtils.packet(tag="stateChange", data="noCamera", metadata="followLine"))
                    mode = "user-control"
            elif (mode == "follow-line"): # Run line following mode
                if newestImage:
                    dist, angle = ComputerVisionUtils.detectLines(newestImage)
                    
                    # Rotation around the x axis aligns to the line
                    xRotTgt = xRotPID(angle)

                    # Rotation around the Y and Z axes keep the robot upright
                    yRotTgt = yRotPID(newestSensorState["imu"]["gyro"]["y"])
                    zRotTgt = zRotPID(newestSensorState["imu"]["gyro"]["z"])

                    # Movement on the x axis keeps a specific distance from the line
                    xPosTgt = xPosPID(dist)

                    speeds = DC.calcMotorValues(xPosTgt, 0, 1, xRotTgt, yRotTgt, zRotTgt)
                    if (time.time() - lastMsgTime > minTime):
                        handlePacket(CommunicationUtils.packet("motorData", speeds, metadata="drivetrain"))
                        lastMsgTime = time.time()
        else:
            if (mode == "user-control"): # Run user control mode
                speeds = DC.calcThrust()
                if (time.time() - lastMsgTime > minTime):
                    handlePacket(CommunicationUtils.packet("motorData", speeds, metadata="drivetrain"))
                    lastMsgTime = time.time()

def receiveVideoStreams(debug=False):
    """ Recieves and processes video from the Water Node then sends it to the Air Node
    
        Arguments:
            debug: (optional) log debugging data
    """

    image_hub = imagezmq.ImageHub(open_port='tcp://*:'+str(CommunicationUtils.CAM_PORT))
    while execute['streamVideo']:
        image_b64 = ""
        imgInfo = ""
        if not simpleMode:
            imgInfo, jpg_buffer = image_hub.recv_jpg()
            image_b64 = jpg_buffer
        else:
            imgInfo, image_raw = image_hub.recv_image()
            image_b64 = CommunicationUtils.encodeImage(image_raw)

        deviceName,timestamp = imgInfo.split("|")
        image_hub.send_reply(b'OK')
        
        imgPacket = CommunicationUtils.packet(tag="cam", data=image_b64, timestamp=timestamp, metadata=deviceName)
        handlePacket(imgPacket)

def receiveData(debug=False):
    """ Recieves and processes JSON data from the Water Node

        Arguments:
            debug: (optional) log debugging data
    """

    HOST = CommunicationUtils.SIMPLE_EARTH_IP if simpleMode else CommunicationUtils.EARTH_IP
    PORT = CommunicationUtils.SNSR_PORT

    snsr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    snsr.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    snsr.bind((HOST, PORT))
    snsr.listen()
    conn, addr = snsr.accept()

    while execute['receiveData']:
        recvPacket = CommunicationUtils.recvMsg(conn)
        handlePacket(recvPacket)
    
    conn.close()
    snsr.close()

def sendData(debug=False):
    """ Sends JSON data to the Water Node

        Arguments:
            debug: (optional) log debugging data
    """
    HOST = CommunicationUtils.SIMPLE_EARTH_IP if simpleMode else CommunicationUtils.EARTH_IP
    PORT = CommunicationUtils.CNTLR_PORT

    cntlr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    cntlr.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    cntlr.bind((HOST, PORT))
    cntlr.listen()
    conn, addr = cntlr.accept()

    while execute['sendData']:
        while not sendDataQueue.empty():
            sendPacket = sendDataQueue.get()
            sent = CommunicationUtils.sendMsg(conn, sendPacket)
    
    conn.close()
    cntlr.close()

def startAirNode(debug=False):
    app = Flask(__name__)

    # Disable Logging
    log = logging.getLogger('werkzeug')
    log.disabled = True
    app.logger.disabled = True

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
        while not airQueue.empty():
            tosend = airQueue.get()
            if (tosend['timestamp'] - time.time() < 0.1):
                socketio.emit("updateAirNode", tosend)
    
    @socketio.on('sendUpdate')
    def getUpdate(recv, methods=["GET","POST"]):
        handlePacket(recv)
        

    def camGen(camName):
        myCamStream = airCamQueues[camName]
        while True:
            time.sleep(settings["camStreamSleep"])
            while not myCamStream.empty():
                camPacket = myCamStream.get()
                tosend = (b'--frame\r\n'+b'Content-Type: image/jpeg\r\n\r\n' + camPacket['data'] + b'\r\n\r\n')
                '''
                if debug:
                    logger.debug("Sending new image to Air Node")
                '''
                yield tosend
                myCamStream.task_done()

    @app.route('/videoFeed/<camName>')
    def videoFeed(camName):
        return Response(camGen(camName), mimetype='multipart/x-mixed-replace; boundary=frame')

    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    socketio.run(app,host=EARTH_IP_WLAN,port=CommunicationUtils.AIR_PORT,debug=False)



if( __name__ == "__main__"):
    # Setup Logging preferences
    verbose = [False,True]

    '''
    # Setup the logger
    logger.setLevel(logging.DEBUG)
    jsonLogHandler = nodeHandler()
    jsonFormatter = jsonlogger.JsonFormatter("%(asctime)s %(name)s %(threadName)s %(levelname)s %(message)s")
    jsonLogHandler.setFormatter(jsonFormatter)
    jsonLogHandler.setLevel(logging.DEBUG)
    logger.addHandler(jsonLogHandler)
    logHandler = logging.StreamHandler()
    logFormatter = logging.Formatter("%(asctime)s - %(name)s - %(threadName)s - %(levelname)s - %(message)s")
    logHandler.setFormatter(logFormatter)
    logHandler.setLevel(logging.INFO)
    logger.addHandler(logHandler)
    
    time.sleep(2)
    # Start each thread
    logger.info("Starting Earth Node")
    logger.debug("Started all Threads")
    '''
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

    # Begin the Shutdown
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
    CommunicationUtils.clearQueue(airQueue)