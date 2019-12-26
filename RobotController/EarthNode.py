# Utility Imports
import sys
import os
import argparse

# Stores if the program is in testing mode or not
simpleMode = False

# Check if the program is in testing mode and enable it if so
parser = argparse.ArgumentParser()
parser.add_argument("-s", "--simple", help="run the program in simple mode (fake data and no special libraries). Useful for running on any device not in the robot", action="store_true")
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
    "bkpCam2": Queue(0)
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

'''
class nodeHandler(logging.Handler):
    def emit(self, record):
        logEntry = json.loads(self.format(record))
        airQueue.put(CommunicationUtils.sendMsg(None, logEntry, "log", None, isString=False, send=False))
logger = logging.getLogger("EarthNode")
'''

def stopAllThreads(callback=0):
    """ Stops all currently running threads
        
        Argument:airQueue
            callback: (optional) callback event
    """

    execute['streamVideo'] = False
    execute['receiveData'] = False
    execute['sendData'] = False
    execute['mainThread'] = False
    '''
    logger.debug("Stopping Threads")
    '''

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
    gamepad = None
    while (not gamepad) and execute['mainThread']:
        time.sleep(5)
        try:
            gamepad = ControllerUtils.identifyController()
        except Exception as e:
            print(e)

    newestImage = []
    newestSensorState = {
        'imu': {
            'calibration': {
                'sys': 2, 
                'gyro': 3, 
                'accel': 0, 
                'mag': 0
            }, 
            'gyro': {
                'x': 0, 
                'y': 0, 
                'z': 0
            },
            'vel': {
                'x': -0.01,
                'y': 0.0,
                'z': -0.29
            }
        },
        'temp': 25
    }

    # Initalize PID controllers
    Kp = 1
    Kd = 0.1
    Ki = 0.05
    xRotPID = PID(Kp, Kd, Ki, setpoint=0)
    yRotPID = PID(Kp, Kd, Ki, setpoint=0)
    zRotPID = PID(Kp, Kd, Ki, setpoint=0)

    mode = "user-control"
    override = False
    print("mode:", mode)
    print("override:", override)

    lastMsgTime = time.time()
    minTime = 1.0/10.0
    while execute['mainThread']:
        while not mainQueue.empty():
            recvMsg = mainQueue.get()
            if recvMsg['tag'] == 'cam':
                #newestImage = CommunicationUtils.decodeImage(recvMsg['data'])
                pass
            elif recvMsg['tag'] == 'sensor':
                newestSensorState = recvMsg['data']

        # Get Joystick Input
        event = gamepad.read_one()
        if event:
            if (ControllerUtils.isOverrideCode(event, action="down")):
                override = True
                print("override:", override)
            elif (ControllerUtils.isOverrideCode(event, action="up") and override):
                override = False
                print("override:", override)
            
            if (ControllerUtils.isStopCode(event)):
                handlePacket(CommunicationUtils.packet("stateChange", "close"))
                time.sleep(1)
                stopAllThreads()
            elif (ControllerUtils.isZeroMotorCode(event)):
                handlePacket(CommunicationUtils.packet("motorData", DC.zeroMotors(), metadata="drivetrain"))
            elif (ControllerUtils.isStabilizeCode(event)):
                if (mode != "stabilize"):
                    # Reset PID controllers
                    xRotPID.reset()
                    yRotPID.reset()
                    zRotPID.reset()
                    xRotPID.tunings = (Kp, Ki, Kd)
                    yRotPID.tunings = (Kp, Ki, Kd)
                    zRotPID.tunings = (Kp, Ki, Kd)

                    # Assuming the robot has been correctly calibrated, (0,0,0) should be upright
                    xRotPID.setpoint = 0
                    yRotPID.setpoint = 0
                    zRotPID.setpoint = 0
                    mode = "stabilize"
                    print("mode:", mode)
                else:
                    mode = "user-control"
                    print("mode:", mode)
            if  (mode == "user-control" or override):
                DC.updateState(event)
                speeds = DC.calcThrust()
                if (time.time() - lastMsgTime > minTime):
                    handlePacket(CommunicationUtils.packet("motorData", speeds, metadata="drivetrain"))
                    lastMsgTime = time.time()
        elif (mode == "stabilize" and not override):
            xTgt = xRotPID(newestSensorState["imu"]["gyro"]["x"])
            yTgt = yRotPID(newestSensorState["imu"]["gyro"]["y"])
            zTgt = zRotPID(newestSensorState["imu"]["gyro"]["z"])
            speeds = DC.calcPIDRot(xTgt,yTgt,zTgt)
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
    
    '''
    logger.info('Sensor Socket Connected by '+str(addr))
    '''

    while execute['receiveData']:
        recvPacket = CommunicationUtils.recvMsg(conn)
        handlePacket(recvPacket)
        '''
        if debug:
            logger.debug("Raw receive: "+str(recv))
            logger.debug("TtS: "+str(time.time()-float(j['timestamp'])))
        '''
        '''
        logger.debug("Couldn't receive data: {}".format(e), exc_info=True)
        '''
    
    conn.close()
    snsr.close()
    '''
    logger.debug("Stopped recvData")
    '''

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

    '''
    logger.info('Motor Socket Connected by '+str(addr))
    '''

    while execute['sendData']:
        while not sendDataQueue.empty():
            sendPacket = sendDataQueue.get()
            sent = CommunicationUtils.sendMsg(conn, sendPacket)
            if debug:
                print(sent)
                '''
                logger.debug("Sending: "+str(sent),extra={"rawData":"true"})
                '''
    
    conn.close()
    cntlr.close()
    '''
    logger.debug("Stopped sendData")
    '''

def startAirNode(debug=False):
    app = Flask(__name__)

    # Disable Logging
    log = logging.getLogger('werkzeug')
    log.disabled = True
    app.logger.disabled = True

    socketio = SocketIO(app)

    @app.route('/copilot')
    def copilot():
        return render_template('copilot.html')

    def messageReceived(methods=['GET', 'POST']):
        print('message was received!!!')

    @socketio.on('getAirNodeUpdates')
    def getAir(recv, methods=["GET","POST"]):
        while not airQueue.empty():
            tosend = airQueue.get()
            #print(tosend['timestamp']-time.time(), tosend['tag'])
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

    @app.route('/left')
    def left():
        return render_template('leftCam_logging.html')

    @app.route('/right')
    def right():
        return render_template('rightCam_cv.html')

    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    socketio.run(app,host='localhost',port=CommunicationUtils.AIR_PORT,debug=False)



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