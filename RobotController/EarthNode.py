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

'''
# Imports for Logging
import logging
from pythonjsonlogger import jsonlogger
'''

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
    "flipMotors": [1]*8,
    "minMotorSpeed": 0,
    "maxMotorSpeed": 180,
    "camStreamSleep": 1.0/30.0
}

# Dict to stop threads
execute = {
    "streamVideo": True,
    "receiveData": True,
    "sendData": True,
    "updateSettings": True,
    "communication": True
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
communicationHandlerQueue = Queue(0)
mainQueue = Queue(0)

# Dict that stores message tags and the threads the go to
tags = {
    "sensor": [airQueue, mainQueue],
    "cam": {
        "mainCam": [airCamQueues["mainCam"],mainQueue],
        "bkpCam1": [airCamQueues["bkpCam1"]],
        "bkpCam2": [airCamQueues["bkpCam2"]],
        },
    "bkpCams": [airQueue],
    "motorData": [sendDataQueue],
    "log": [airQueue],
    "stateChange": [airQueue,recvDataQueue,sendDataQueue,recvImageQueue,mainQueue]
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
    execute['updateSettings'] = False
    execute['communicationHandler'] = False
    '''
    logger.debug("Stopping Threads")
    '''

def communicationHandler(debug=False):
    """ Handles communication between all of the other threads

        Arguments:
            debug: (optional) log debugging data
    """
    while execute['communicationHandler']:
        while not communicationHandlerQueue.empty():
            qData = communicationHandlerQueue.get()
            if qData['tag'] in tags:
                if qData['tag'] ==  "cam":
                    for threadQueue in tags[qData['tag']][qData['metadata']]:
                        threadQueue.put(qData)
                else:
                    for threadQueue in tags[qData['tag']]:
                        threadQueue.put(qData)

def receiveVideoStreams(debug=False):
    """ Recieves and processes video from the Water Node then sends it to the Air Node
    
        Arguments:
            debug: (optional) log debugging data
    """

    image_hub = imagezmq.ImageHub(open_port='tcp://*:'+str(CommunicationUtils.CAM_PORT))
    print(simpleMode)
    while execute['streamVideo']:
        image_raw = ""
        imgInfo = ""
        if not simpleMode:
            imgInfo, jpg_buffer = image_hub.recv_jpg()
            image_raw = cv2.imdecode(np.frombuffer(jpg_buffer, dtype='uint8'), -1)
        else:
            imgInfo, image_raw = image_hub.recv_image()

        deviceName,timestamp = imgInfo.split("|")
        image_hub.send_reply(b'OK')
        image_b64 = CommunicationUtils.encodeImage(image_raw)
        
        imgPacket = CommunicationUtils.packet("img", image_b64, timestamp, deviceName)
        communicationHandlerQueue.put(imgPacket)

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
        try:
            recvPacket = CommunicationUtils.recvMsg(conn)
            communicationHandlerQueue.put(recvPacket)
            '''
            if debug:
                logger.debug("Raw receive: "+str(recv))
                logger.debug("TtS: "+str(time.time()-float(j['timestamp'])))
            '''
        except Exception as e:
            print(e)
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

    # Start the update settings thread
    updtSettingsThread = threading.Thread(target=updateSettings, args=(conn,debug,))
    updtSettingsThread.start()

<<<<<<< HEAD
    # Start Controller
    gamepad = None
    while (not gamepad) and execute['sendData']:
        time.sleep(5)
        try:
            gamepad = ControllerUtils.identifyController()
        except Exception as e:
            print(e)

    DC = ControllerUtils.DriveController()

    while execute['sendData']:
        event = gamepad.read_one()
        if event:
            if (ControllerUtils.isStopCode(event)):
                CommunicationUtils.sendMsg(conn, "closing", "connInfo", "None", repetitions=2)
                logger.debug("Sending shutdown signal to Water Node")
                time.sleep(1)
                stopAllThreads()
            elif (ControllerUtils.isZeroMotorCode(event)):
                CommunicationUtils.sendMsg(conn, [90]*settings['numMotors'], "motorSpds", "zeroMotors", isString=False)
                logger.debug("Zeroed Motors Manually")
            else:
                DC.updateState(event)
                speeds = DC.calcThrust(event)
                sent = CommunicationUtils.sendMsg(conn, speeds, "thrustSpds", "None", isString=False, lowPriority=True)
                airQueue.put(sent)
=======
    while execute['sendData']:
        while not sendDataQueue.empty():
            sendPacket = sendDataQueue.get()
            if sendPacket["tag"] == "motor":
                sent = CommunicationUtils.sendMsg(conn, sendPacket)
>>>>>>> temp
            if debug:
                print(sendPacket)
                '''
                logger.debug("Sending: "+str(sent),extra={"rawData":"true"})
                '''

    updtSettingsThread.join()
    
    conn.close()
    cntlr.close()
    '''
    logger.debug("Stopped sendData")
    '''

def updateSettings(sckt,debug=False):
    """ Receives setting updates from the Air Node and makes edits
        Most changes will be made to settings in the Earth Node, but some will be sent to the Water Node
        Arguments:
            sckt: socket to communicate with the Water Node
            debug: (optional) log debugging data
    """
    # Wait until a setting is updated, then make the change and or sent data to the water node
    while execute['updateSettings']:
        time.sleep(2)
    '''
    logger.debug("Stopped updateSettings")
    '''

def startAirNode(debug=False):
    app = Flask(__name__)

    '''
    # Disable Logging
    log = logging.getLogger('werkzeug')
    log.disabled = True
    '''
    app.logger.disabled = True

    socketio = SocketIO(app)

    @app.route('/')
    def index():
        return render_template('mid_sensors.html')

    def messageReceived(methods=['GET', 'POST']):
        print('message was received!!!')

    @socketio.on('getAirNodeUpdates')
    def getAir(recv, methods=["GET","POST"]):
        while not airQueue.empty():
            tosend = airQueue.get()
            socketio.emit("updateAirNode", tosend)

    def camGen(camName):
<<<<<<< HEAD
        myCamStream = camStreams[camName]
=======
        myCamStream = airCamQueues[camName]
>>>>>>> temp
        while True:
            time.sleep(settings["camStreamSleep"])
            while not myCamStream.empty():
                tosend = (b'--frame\r\n'+b'Content-Type: image/jpeg\r\n\r\n' + myCamStream.get() + b'\r\n\r\n')
<<<<<<< HEAD
=======
                '''
>>>>>>> temp
                if debug:
                    logger.debug("Sending new image to Air Node")
                '''
                yield tosend
                myCamStream.task_done()

    @app.route('/videoFeed/<camName>')
<<<<<<< HEAD
    def mainCam(camName):
=======
    def videoFeed(camName):
>>>>>>> temp
        return Response(camGen(camName),
                        mimetype='multipart/x-mixed-replace; boundary=frame')

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

    vidStreamThread = threading.Thread(target=receiveVideoStreams, args=(verbose[0],), daemon=True)
    recvDataThread = threading.Thread(target=receiveData, args=(verbose[0],))
    sendDataThread = threading.Thread(target=sendData, args=(verbose[0],))
    #airNodeThread = threading.Thread(target=startAirNode, args=(verbose[0],), daemon=True)
    commHandlerThread = threading.Thread(target=communicationHandler, args=(verbose[0],))
    vidStreamThread.start()
    recvDataThread.start()
    sendDataThread.start()
    #airNodeThread.start()

    # Begin the Shutdown
    while execute['streamVideo'] or execute['receiveData'] or execute['sendData'] or execute['updateSettings']:
        time.sleep(0.1)
    recvDataThread.join()
    sendDataThread.join()
    vidStreamThread.join()
    #airNodeThread.join()
    '''
    logger.debug("Stopped all Threads")
    logger.info("Shutting Down Ground Node")
    '''
    CommunicationUtils.clearQueue(airQueue)