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

# Settings Dict to keep track of editable settings for data processing
settings = {
    "numCams": 4,
    "drive": "holonomic",
    "numMotors": 6,
    "flipMotors": [1]*6
}

# Dict to stop threads
execute = {
    "streamVideo": True,
    "receiveData": True,
    "sendData": True,
    "updateSettings": True
}

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

def receiveVideoStreams(display=False,debug=False):
    """ Recieves and processes video from the Water Node

        Arguments:
            display: (optional) display recieved images using OpenCV
            debug: (optional) log debugging data
    """

    image_hub = imagezmq.ImageHub()
    while execute['streamVideo']:
        deviceName, image = image_hub.recv_image()
        if(display):
            cv2.imshow(deviceName, image)
            cv2.waitKey(1)
        image_hub.send_reply(b'OK')
    logging.debug("Stopped VideoStream")

def receiveData(debug=False):
    """ Recieves and processes JSON data from the Water Node

        Data will most likely be sensor data from an IMU and voltage/amperage sensor

        Arguments:
            debug: (optional) log debugging data
    """

    HOST = '127.0.0.1'
    PORT = 65432

    snsr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        snsr.bind((HOST, PORT))
        snsr.listen()
        conn, addr = snsr.accept()
        logging.info('Sensor Connected by'+str(addr))

        while execute['receiveData']:
                recv = CommunicationUtils.recvMsg(conn)
                j = json.loads(recv)
                if debug:
                    logging.debug("Raw receive: "+str(recv))
                    logging.debug("TtS: "+str(time.time()-float(j['timestamp'])))
        CommunicationUtils.closeSocket(snsr)
    except Exception as e:
        logging.critical("receive Exception Occurred",exc_info=True)
        CommunicationUtils.closeSocket(snsr)
    logging.debug("Stopped recvData")

def sendData(debug=False):
    """ Sends JSON data to the Water Node

        Data will most likel contain motor data, and settings changes

        Arguments:
            debug: (optional) log debugging data
    """
    HOST = '127.0.0.1'
    PORT = 65432

    cntlr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        cntlr.connect((HOST, PORT))
        updtSettingsThread = threading.Thread(target=updateSettings, args=(cntlr,debug,))
        updtSettingsThread.start()
        while execute['sendData']:
            sent = CommunicationUtils.sendMsg(cntlr,[90]*6,"motors","None")
            if debug:
                logging.debug("Sending: "+str(sent))
        CommunicationUtils.closeSocket(cntlr)
        updtSettingsThread.join()
    except Exception as e:
        logging.error("Send Exception Occurred",exc_info=True)
        CommunicationUtils.closeSocket(cntlr)
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

if( __name__ == "__main__"):
    verbose = False
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)

    keyboard.on_press_key("q", stopAllThreads, suppress=False)

    vidStreamThread = threading.Thread(target=receiveVideoStreams, args=(True,verbose,),daemon=True)
    recvDataThread = threading.Thread(target=receiveData, args=(verbose,))
    vidStreamThread.start()
    recvDataThread.start()
    sendData(verbose)
    vidStreamThread.join(timeout=5)
    recvDataThread.join()
    logging.debug("Stopped all Threads")
    logging.info("Shutting Down Program")
    sys.exit()