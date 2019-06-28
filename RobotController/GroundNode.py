# Imports for Logging
import logging
from pythonjsonlogger import jsonlogger


# Imports for Threading
import threading
import keyboard
from queue import Queue

# Imports for Video Streaming
import sys
sys.path.insert(0, 'imagezmq/imagezmq')

import cv2
import imagezmq

# Imports for Socket Communication
import socket
import CommunicationUtils
import simplejson as json
import time
import keyboard
import websocket

# Imports for Controller Communication and Processing
import ControllerUtils
import evdev

# Imports for AirNode
from flask import Flask, render_template, Response

# Settings Dict to keep track of editable settings for data processing
settings = {
    "numCams": 4,
    "maxCams": 4,
    "drive": "holonomic",
    "numMotors": 6,
    "flipMotors": [1]*6,
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

class nodeHandler(logging.Handler):
    def emit(self, record):
        global groundQueue

        logEntry = self.format(record)
        airQueue.put(CommunicationUtils.sendMsg(None, logEntry, "log", None, isString=False, send=False))

logger = logging.getLogger("GroundNode")


def stopAllThreads(callback=0):
    """ Stops all currently running threads
        
        Argument:airQueue
            callback: (optional) callback event
    """

    execute['streamVideo'] = False
    execute['receiveData'] = False
    execute['sendData'] = False
    execute['updateSettings'] = False
    logger.debug("Stopping Threads")

def receiveVideoStreams(debug=False):
    """ Recieves and processes video from the Water Node then sends it to the Air Node

        Arguments:
            debug: (optional) log debugging data
    """

    try:

        image_hub = imagezmq.ImageHub()
        while execute['streamVideo']:
            deviceName, image = image_hub.recv_image()
            if debug:
                logger.debug("Recieved new image from Ground Node")
                logger.debug(image)
            image_hub.send_reply(b'OK')
            camStreams[deviceName].put(CommunicationUtils.encodeImage(image))
    except Exception as e:
        logger.error("Video Streaming Thread Exception Occurred: {}".format(e), exc_info=True)
    logger.debug("Stopped VideoStream")

def receiveData(debug=False):
    """ Recieves and processes JSON data from the Water Node

        Data will most likely be sensor data from an IMU and voltage/amperage sensor

        Arguments:
            debug: (optional) log debugging data
    """

    HOST = '127.0.0.1'
    PORT = CommunicationUtils.SNSR_PORT

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as snsr:
        try:
            try:
                snsr.bind((HOST, PORT))
            except:
                try:
                    logger.error("Couldn't establish connection. Port {} is already in use".format(PORT))
                    time.sleep(10)
                    cntlr.bind((HOST, PORT))
                except:
                    logger.error("Try again in a bit. Port {} is still busy".format(PORT))
                    stopAllThreads()
            snsr.listen()
            conn, addr = snsr.accept()
            logger.info('Sensor Socket Connected by '+str(addr))

            while execute['receiveData']:
                try:
                    recv = CommunicationUtils.recvMsg(conn)
                    airQueue.put(recv)
                    j = json.loads(recv)
                    if debug:
                        logger.debug("Raw receive: "+str(recv))
                        logger.debug("TtS: "+str(time.time()-float(j['timestamp'])))
                except Exception as e:
                    logger.debug("Couldn't receive data: {}".format(e), exc_info=True)
        except Exception as e:
            logger.error("Receive Thread Exception Occurred: {}".format(e), exc_info=True)
    logger.debug("Stopped recvData")

def sendData(debug=False):
    """ Sends JSON data to the Water Node

        Data will most likely contain motor data, and settings changes

        Arguments:
            debug: (optional) log debugging data
    """
    HOST = '127.0.0.1'
    PORT = CommunicationUtils.CNTLR_PORT

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cntlr:
        try:
        
            # Setup socket communication
            try:
                cntlr.bind((HOST, PORT))
            except:
                try:
                    logger.error("Couldn't establish connection. Port {} is already in use".format(PORT))
                    time.sleep(10)
                    cntlr.bind((HOST, PORT))
                except:
                    logger.error("Try again in a bit. Port {} is still busy".format(PORT))
                    stopAllThreads()

            cntlr.listen()
            conn, addr = cntlr.accept()
            logger.info('Motor Socket Connected by '+str(addr))

            # Start the update settings thread
            updtSettingsThread = threading.Thread(target=updateSettings, args=(conn,debug,))
            updtSettingsThread.start()

            # Start Controller
            gamepad = ControllerUtils.identifyControllers()
            while (not gamepad) and execute['sendData']:
                time.sleep(5)
                gamepad = ControllerUtils.identifyControllers()

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
                        ControllerUtils.processEvent(event)
                        speeds = ControllerUtils.calcThrust()
                        sent = CommunicationUtils.sendMsg(conn, speeds, "motorSpds", "None", isString=False, lowPriority=True)
                        airQueue.put(sent)
                    if debug:
                        logger.debug("Sending: "+str(sent),extra={"rawData":"true"})

            updtSettingsThread.join()

        except Exception as e:
            logger.error("Send Thread Exception Occurred: {}".format(e), exc_info=True)
    logger.debug("Stopped sendData")

def updateSettings(sckt,debug=False):
    """ Receives setting updates from the Air Node and makes edits

        Most changes will be made to settings in the Ground Node, but some will be sent to the Water Node

        Arguments:
            sckt: socket to communicate with the Water Node
            debug: (optional) log debugging data
    """
    # Wait until a setting is updated, then make the change and or sent data to the water node
    while execute['updateSettings']:
        time.sleep(2)
    logger.debug("Stopped updateSettings")

def startAirNode(debug=False):
    camStreamSleep = 0.03

    app = Flask(__name__)
    # Disable Logging
    log = logging.getLogger('werkzeug')
    log.disabled = True
    app.logger.disabled = True

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/getAir')
    def getAir():
        if not airQueue.empty():
            tosend = json.dumps(airQueue.get())
            airQueue.task_done()
            return Response(tosend,
                        mimetype='application/json')

    def mainCamGen():
        myCamStream = camStreams["mainCam"]
        while True:
            time.sleep(camStreamSleep)
            while not myCamStream.empty():
                tosend = (b'--frame\r\n'+b'Content-Type: image/jpeg\r\n\r\n' + myCamStream.get() + b'\r\n')
                if debug:
                    logger.debug("Sending new image to Air Node")
                yield tosend
                myCamStream.task_done()

    @app.route('/mainCam')
    def mainCam():
        return Response(mainCamGen(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')


    def bkpCam1Gen():
        myCamStream = camStreams["bkpCam2"]
        while True:
            time.sleep(camStreamSleep)
            while not myCamStream.empty():
                tosend = (b'--frame\r\n'+b'Content-Type: image/jpeg\r\n\r\n' + myCamStream.get() + b'\r\n')
                if debug:
                    logger.debug("Sending new image to Air Node")
                yield tosend
                myCamStream.task_done()

    @app.route('/bkpCam1')
    def bkpCam1():
        return Response(bkpCam1Gen(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')


    def bkpCam2Gen():
        myCamStream = camStreams["bkpCam2"]
        while True:
            time.sleep(camStreamSleep)
            while not myCamStream.empty():
                tosend = (b'--frame\r\n'+b'Content-Type: image/jpeg\r\n\r\n' + myCamStream.get() + b'\r\n')
                if debug:
                    logger.debug("Sending new image to Air Node")
                yield tosend
                myCamStream.task_done()

    @app.route('/bkpCam2')
    def bkpCam2():
        return Response(bkpCam2Gen(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')


    def bkpCam3Gen():
        myCamStream = camStreams["bkpCam3"]
        while True:
            time.sleep(camStreamSleep)
            while not myCamStream.empty():
                tosend = (b'--frame\r\n'+b'Content-Type: image/jpeg\r\n\r\n' + myCamStream.get() + b'\r\n')
                if debug:
                    logger.debug("Sending new image to Air Node")
                yield tosend
                myCamStream.task_done()

    @app.route('/bkpCam3')
    def bkpCam3():
        return Response(bkpCam3Gen(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')

    app.run(host='127.0.0.1',port=CommunicationUtils.AIR_PORT,debug=False)


if( __name__ == "__main__"):
    # Setup Logging preferences
    verbose = [False,True]

    # Setup a callback to force stop the program
    keyboard.on_press_key("q", stopAllThreads, suppress=False)

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

    # Start each thread
    logger.info("Starting Ground Node")
    logger.debug("Started all Threads")
    vidStreamThread = threading.Thread(target=receiveVideoStreams, args=(verbose[0],), daemon=True)
    recvDataThread = threading.Thread(target=receiveData, args=(verbose[0],))
    sendDataThread = threading.Thread(target=sendData, args=(verbose[0],))
    airNodeThread = threading.Thread(target=startAirNode, args=(False,), daemon=True)
    vidStreamThread.start()
    recvDataThread.start()
    sendDataThread.start()
    airNodeThread.start()

    # Begin the Shutdown
        # Because there is no timeout on recvDataThread or sendDataThread, they won't join until manually stopped
        # It's a bit of a hack, but it stops the program from shuting down instantly
    recvDataThread.join()
    sendDataThread.join()
    vidStreamThread.join(timeout=5)
    airNodeThread.join(timeout=5)
    logger.debug("Stopped all Threads")
    logger.info("Shutting Down Ground Node")
    for camName in camStreams:
        CommunicationUtils.clearQueue(camStreams[camName])
    CommunicationUtils.clearQueue(airQueue)
    sys.exit()