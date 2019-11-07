# Utility Imports
import sys
import os

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
    "maxMotorSpeed": 180
}

# Dict to stop threads
execute = {
    "streamVideo": True,
    "receiveData": True,
    "sendData": True,
    "updateSettings": True
}

# Dict to store camera stream queues
camStreams = {
    "mainCam": Queue(0)
}

for i in range(0, settings['maxCams']):
    camStreams.update({"bkpCam"+str(i): Queue(0)})

airQueue = Queue(0)

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
    '''
    logger.debug("Stopping Threads")
    '''

def receiveVideoStreams(debug=False):
    """ Recieves and processes video from the Water Node then sends it to the Air Node

        Arguments:
            debug: (optional) log debugging data
    """

    try:

        image_hub = imagezmq.ImageHub(open_port='tcp://*:'+str(CommunicationUtils.CAM_PORT))
        while execute['streamVideo']:
            deviceName, jpg_buffer = image_hub.recv_jpg()
            #deviceName, image = image_hub.recv_image()
            '''
            if debug:
                logger.debug("Recieved new image from Earth Node")
                logger.debug(jpg_buffer)
            '''
            image_hub.send_reply(b'OK')
            image = cv2.imdecode(np.frombuffer(jpg_buffer, dtype='uint8'), -1)
            camStreams[deviceName].put(CommunicationUtils.encodeImage(image))
    except Exception as e:
        pass
    '''
        logger.error("Video Streaming Thread Exception Occurred: {}".format(e), exc_info=True)
    logger.debug("Stopped VideoStream")
    '''

def receiveData(debug=False):
    """ Recieves and processes JSON data from the Water Node

        Data will most likely be sensor data from an IMU and voltage/amperage sensor

        Arguments:
            debug: (optional) log debugging data
    """

    HOST = CommunicationUtils.EARTH_IP
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
            recv = CommunicationUtils.recvMsg(conn)
            airQueue.put(recv)
            j = json.loads(recv)
            '''
            if debug:
                logger.debug("Raw receive: "+str(recv))
                logger.debug("TtS: "+str(time.time()-float(j['timestamp'])))
            '''
        except Exception as e:
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

        Data will most likely contain motor data, and settings changes

        Arguments:
            debug: (optional) log debugging data
    """
    HOST = CommunicationUtils.EARTH_IP
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

    # Start Controller
    gamepad = None
    while (not gamepad) and execute['sendData']:
        time.sleep(5)
        try:
            gamepad = ControllerUtils.identifyControllers()
        except Exception as e:
            print(e)

    #DC = ControllerUtils.DriveController()

    while execute['sendData']:
        event = gamepad.read_one()
        if event:
            if (ControllerUtils.isStopCode(event)):
                CommunicationUtils.sendMsg(conn, "closing", "connInfo", "None", repetitions=2)
                '''
                logger.debug("Sending shutdown signal to Water Node")
                '''
                time.sleep(1)
                stopAllThreads()
            elif (ControllerUtils.isZeroMotorCode(event)):
                CommunicationUtils.sendMsg(conn, [90]*settings['numMotors'], "motorSpds", "zeroMotors", isString=False)
                '''
                logger.debug("Zeroed Motors Manually")
                '''
            else:
                DC.updateState(event)
                #speeds = DC.calcThrust(event)
                sent = CommunicationUtils.sendMsg(conn, speeds, "thrustSpds", "None", isString=False, lowPriority=True)
                airQueue.put(sent)
            if debug:
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
    camStreamSleep = 0.03

    app = Flask(__name__)

    '''
    # Disable Logging
    log = logging.getLogger('werkzeug')
    log.disabled = True
    app.logger.disabled = True
    '''

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

    def mainCamGen():
        myCamStream = camStreams["mainCam"]
        while True:
            time.sleep(camStreamSleep)
            while not myCamStream.empty():
                tosend = (b'--frame\r\n'+b'Content-Type: image/jpeg\r\n\r\n' + myCamStream.get() + b'\r\n')
                '''
                if debug:
                    logger.debug("Sending new image to Air Node")
                '''
                yield tosend
                myCamStream.task_done()

    @app.route('/mainCam')
    def mainCam():
        return Response(mainCamGen(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')

    @app.route('/left')
    def left():
        return render_template('leftCam_logging.html')

    def bkpCam1Gen():
        myCamStream = camStreams["bkpCam2"]
        while True:
            time.sleep(camStreamSleep)
            while not myCamStream.empty():
                tosend = (b'--frame\r\n'+b'Content-Type: image/jpeg\r\n\r\n' + myCamStream.get() + b'\r\n')
                '''
                if debug:
                    logger.debug("Sending new image to Air Node")
                '''
                yield tosend
                myCamStream.task_done()

    @app.route('/bkpCam1')
    def bkpCam1():
        return Response(bkpCam1Gen(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')


    @app.route('/right')
    def right():
        return render_template('rightCam_cv.html')

    def bkpCam2Gen():
        myCamStream = camStreams["bkpCam2"]
        while True:
            time.sleep(camStreamSleep)
            while not myCamStream.empty():
                tosend = (b'--frame\r\n'+b'Content-Type: image/jpeg\r\n\r\n' + myCamStream.get() + b'\r\n')
                '''
                if debug:
                    logger.debug("Sending new image to Air Node")
                '''
                yield tosend
                myCamStream.task_done()
 
    @app.route('/bkpCam2')
    def bkpCam2():
        return Response(bkpCam2Gen(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')

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
    airNodeThread = threading.Thread(target=startAirNode, args=(False,), daemon=True)
    vidStreamThread.start()
    recvDataThread.start()
    sendDataThread.start()
    airNodeThread.start()

    # Begin the Shutdown
    while execute['streamVideo'] or execute['receiveData'] or execute['sendData'] or execute['updateSettings']:
        time.sleep(0.1)
    recvDataThread.join(timeout=5)
    sendDataThread.join(timeout=5)
    vidStreamThread.join(timeout=5)
    airNodeThread.join(timeout=5)
    '''
    logger.debug("Stopped all Threads")
    logger.info("Shutting Down Ground Node")
    '''
    for camName in camStreams:
        CommunicationUtils.clearQueue(camStreams[camName])
    CommunicationUtils.clearQueue(airQueue)
