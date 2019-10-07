# Utility Imports
import sys
import os

# Imports for Logging
import logging
from pythonjsonlogger import jsonlogger

# Imports for Threading
import threading
from queue import Queue

# Imports for Video Streaming
sys.path.insert(0, 'imagezmq/imagezmq')

import cv2
import imagezmq

# Imports for Socket Communication
import socket
import CommunicationUtils
import simplejson as json
import time

# Imports for Hardware Interfacing
import HardwareUtils

# Settings Dict to keep track of editable settings for data processing
settings = {
	"numCams": 3,
    "maxCams": 3,
	"numMotors": 8,
	"minMotorSpeed": 0,
	"maxMotorSpeed": 180,
	"streamingQuality": 10,
	"mainCameraResolution": (1280, 720),
	"backupCameraResolution": (480,270)
}

# Dict to stop threads
execute = {
	"streamVideo": True,
	"sendData": True,
	"receiveData": True
}

# Queue, Logger, and Class for Multithreaded Logging Communication
earthQueue = Queue(0)

class nodeHandler(logging.Handler):
	def emit(self, record):
		global earthQueue

		logEntry = self.format(record)
		earthQueue.put([json.loads(logEntry),"log",False,False])

logger = logging.getLogger("WaterNode")


def stopAllThreads(callback=0):
	""" Stops all currently running threads
		
		Argument:
			callback: (optional) callback event
	"""

	execute['streamVideo'] = False
	execute['receiveData'] = False
	execute['sendData'] = False
	logger.debug("Stopping Threads")
	time.sleep(0.5)

def sendVideoStreams(debug=False):
	""" Sends video from each camera to the Earth Node

		Arguments:
			debug: (optional) log debugging data
	"""

	sender = imagezmq.ImageSender(connect_to='tcp://'+CommunicationUtils.EARTH_IP+':'+str(CommunicationUtils.CAM_PORT))
	logger.debug("Sending images to port: "+'tcp://'+CommunicationUtils.EARTH_IP+':'+str(CommunicationUtils.CAM_PORT))

	camNames = ["mainCam"]
	camCaps = [cv2.VideoCapture(0)]

	for i in range(1,settings['numCams']):
		camNames.append("bkpCam"+str(i))
		camCaps.append(camCaps[0] #cv2.VideoCapture(i)) ### UPDATE LATER TO USE ADDITIONAL CAMERAS
	numCams = len(camCaps)
	logger.debug('Cam names and Objects: '+str(camNames)+', '+str(camCaps))

	time.sleep(2.0)
	try:
		while execute['streamVideo']:
			for i in range(0,numCams):
				_, img = camCaps[i].read()
				resized = cv2.resize(img, settings["mainCameraResolution"], interpolation=cv2.INTER_CUBIC)
				ret_code, jpg_buffer = cv2.imencode(".jpg", resized, [int(cv2.IMWRITE_JPEG_QUALITY), settings['streamingQuality']])
				try:
					sender.send_jpg(camNames[i], jpg_buffer)
				except:
					logger.warning("Invalid Image: "+str(jpg_buffer))
					time.sleep(1)
				if debug:
					logger.debug("Sent Image: "+str(jpg_buffer[:1][:1]))
	except Exception as e:
		logger.error("VideoStream Thread Exception Occurred: {}".format(e), exec_info=True)
	logger.debug("Stopped VideoStream")

def receiveData(debug=False):
	""" Recieves and processes JSON data from the Water Node
		
		Data will most likely contain motor data, and settings changes

		Arguments:
			debug: (optional) log debugging data
	"""

	HOST = CommunicationUtils.EARTH_IP
	PORT = CommunicationUtils.CNTLR_PORT
	
	SD = HardwareUtils.ServoDriver(enumerate(["T100"]*8))

	try:
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cntlr:
			cntlr.connect((HOST, PORT))
			while execute['receiveData']:
					recv = "{}"
					try:
						recv = CommunicationUtils.recvMsg(cntlr)
						j = json.loads(recv)
						if j['dataType'] == "connInfo" and j['data'] == "closing":
							stopAllThreads()
						
						elif j['dataType'] == "thrustSpds":
							for loc,spd in enumerate(j['data']):
								SD.set_servo(loc,spd)

						if debug:
							logger.debug("Raw receive: "+str(recv))
							logger.debug("TtS: "+str(time.time()-float(j['timestamp'])))
					except Exception as e:
						logger.debug("Couldn't recieve data: {}".format(e), exc_info=True)

	except Exception as e:
		logger.error("Receive Thread Exception Occurred", exc_info=True)
	logger.debug("Stopped recvData")

def sendData(sendQueue,debug=False):
	""" Sends JSON data to the Water Node

		Data will most likely be sensor data from an IMU and voltage/amperage sensor

		Arguments:
			debug: (optional) log debugging data
	"""
	HOST = CommunicationUtils.EARTH_IP
	PORT = CommunicationUtils.SNSR_PORT

	try:
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as snsr:
			snsr.connect((HOST, PORT))
			while execute['sendData']:
				# Get gyro, accel, voltage, amperage readings
				sensors = {
					"gyro": {
						"x": 0,
						"y": 0,
						"z": 0,
					},
					"speed": 0,
					"volts": 0,
					"amps": 0
				}
				sendQueue.put([sensors,"sensors",False,True])
				time.sleep(0.0125)
				while not sendQueue.empty():
					toSend = sendQueue.get()
					try:
						sent = CommunicationUtils.sendMsg(snsr,toSend[0],toSend[1],"None",isString=toSend[2],lowPriority=toSend[3])
						if debug:
							logger.debug("Sending: "+str(sent))

					except Exception as e:
						logger.warning("Couldn't send data: {}".format(e), exc_info=True)

					sendQueue.task_done()

	except Exception as e:
		logger.error("Send Thread Exception Occurred: {}".format(e), exc_info=True)
	logger.debug("Stopped sendData")

if( __name__ == "__main__"):
	# Setup Logging preferences
	verbose = [False,True]

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
	logger.info("Starting Water Node")
	logger.debug("Started all Threads")
	vidStreamThread = threading.Thread(target=sendVideoStreams, args=(verbose[0],),daemon=True)
	recvDataThread = threading.Thread(target=receiveData, args=(verbose[0],),daemon=True)
	sendDataThread = threading.Thread(target=sendData, args=(earthQueue,verbose[0],),daemon=True)
	vidStreamThread.start()
	recvDataThread.start()
	sendDataThread.start()

	# Begin the Shutdown
	while execute['streamVideo'] or execute['receiveData'] or execute['sendData']:
		time.sleep(0.1)
	recvDataThread.join(timeout=5)
	sendDataThread.join(timeout=5)
	vidStreamThread.join(timeout=5)
	logger.debug("Stopped all Threads")
	logger.info("Shutting Down Water Node")
	CommunicationUtils.clearQueue(earthQueue)

	sys.exit()
