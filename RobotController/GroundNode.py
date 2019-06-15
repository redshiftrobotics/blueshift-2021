# Imports for Logging
import logging

# Imports for Threading
import threading
import keyboard

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

# Dict to store camera streams
camStreams = {
    "mainCam": b''
}

#for i in range(0, settings['numCams']):
#    camStreams.update({"bkpCam"+str(i):b''})


def stopAllThreads(callback=0):
    """ Stops all currently running threads
        
        Argument:
            callback: (optional) callback event
    """

    execute['streamVideo'] = False
    execute['receiveData'] = False
    execute['sendData'] = False
    execute['updateSettings'] = False
    logging.debug("Stopping Threads")

def receiveVideoStreams(debug=False):
    """ Recieves and processes video from the Water Node then sends it to the Air Node

        Arguments:
            debug: (optional) log debugging data
    """

    try:
        airNodeThread = threading.Thread(target=startAirNode,daemon=True)
        airNodeThread.start()

        image_hub = imagezmq.ImageHub()
        while execute['streamVideo']:
            deviceName, image = image_hub.recv_image()
            if debug:
                logging.debug(image)
            image_hub.send_reply(b'OK')
            camStreams.update({deviceName: CommunicationUtils.encodeImage(image)})
            logging.debug("Recieved new image from Ground Node")
        airNodeThread.join(5)
    except Exception as e:
        logging.error("Video Streaming Thread Exception Occurred",exc_info=True)
    logging.debug("Stopped VideoStream")

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
                    logging.error("Couldn't establish connection. Port {} is already in use".format(PORT))
                    time.sleep(10)
                    cntlr.bind((HOST, PORT))
                except:
                    logging.error("Try again in a bit. Port {} is still busy".format(PORT))
                    stopAllThreads()
            snsr.listen()
            conn, addr = snsr.accept()
            logging.info('Sensor Socket Connected by '+str(addr))

            while execute['receiveData']:
                try:
                    recv = CommunicationUtils.recvMsg(conn)
                    j = json.loads(recv)
                    if debug:
                        logging.debug("Raw receive: "+str(recv))
                        logging.debug("TtS: "+str(time.time()-float(j['timestamp'])))
                except Exception as e:
                    logging.debug("Couldn't receive data",exec_info=True)
        except Exception as e:
            logging.error("Receive Thread Exception Occurred",exc_info=True)
    logging.debug("Stopped recvData")

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
                    logging.error("Couldn't establish connection. Port {} is already in use".format(PORT))
                    time.sleep(10)
                    cntlr.bind((HOST, PORT))
                except:
                    logging.error("Try again in a bit. Port {} is still busy".format(PORT))
                    stopAllThreads()

            cntlr.listen()
            conn, addr = cntlr.accept()
            logging.info('Motor Socket Connected by '+str(addr))

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
                        logging.debug(CommunicationUtils.sendMsg(conn,"closing","connInfo","None",repetitions=2))
                        time.sleep(1)
                        stopAllThreads()

                    ControllerUtils.processEvent(event)
                    speeds = ControllerUtils.calcThrust()
                    sent = CommunicationUtils.sendMsg(conn,speeds,"motorSpds","None",isString=False)
                    if debug:
                        time.sleep(1)
                        logging.debug("Sending: "+str(sent))

            updtSettingsThread.join()

        except Exception as e:
            logging.error("Send Thread Exception Occurred",exc_info=True)
    logging.debug("Stopped sendData")

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
    logging.debug("Stopped updateSettings")

def startAirNode():
    app = Flask(__name__)

    @app.route('/')
    def index():
        return render_template('index.html')

    def mainCamGen():
        global counter
        while True:
            time.sleep(0.001)
            tosend = (b'--frame\r\n'+b'Content-Type: image/jpeg\r\n\r\n' + camStreams["mainCam"] + b'\r\n')
            logging.debug("Sending new image to Air Node")
            yield tosend

    @app.route('/mainCam')
    def mainCam():
        return Response(mainCamGen(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')

    app.run(host='127.0.0.1',port=5000)


if( __name__ == "__main__"):
    # Setup Logging preferences
    verbose = [False,True]
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)

    # Setup a callback to force stop the program
    keyboard.on_press_key("q", stopAllThreads, suppress=False)

    # Start each thread
    logging.info("Starting Ground Node")
    logging.debug("Started all Threads")
    vidStreamThread = threading.Thread(target=receiveVideoStreams, args=(verbose[0],),daemon=True)
    recvDataThread = threading.Thread(target=receiveData, args=(verbose[0],))
    sendDataThread = threading.Thread(target=sendData, args=(verbose[0],))
    vidStreamThread.start()
    recvDataThread.start()
    sendDataThread.start()

    # Begin the Shutdown
        # Because there is no timeout on recvDataThread or sendDataThread, they won't join until manually stopped
        # It's a bit of a hack, but it stops the program from shuting down instantly
    recvDataThread.join()
    sendDataThread.join()
    vidStreamThread.join(timeout=5)
    logging.debug("Stopped all Threads")
    logging.info("Shutting Down Ground Node")
    sys.exit()