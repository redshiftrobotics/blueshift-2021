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

# Settings Dict to keep track of editable settings for data processing
settings = {
	"numCams": 4,
    "maxCams": 4,
	"numMotors": 6,
	"minMotorSpeed": 0,
	"maxMotorSpeed": 180
}

# Dict to stop threads
execute = {
	"streamVideo": True,
	"sendData": True,
	"receiveData": True
}

# Queue, Logger, and Class for Multithreaded Logging Communication
groundQueue = Queue(0)

class nodeHandler(logging.Handler):
	def emit(self, record):
		global groundQueue

		logEntry = self.format(record)
		groundQueue.put([logEntry,"log",False,False])

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
	""" Sends video from each camera to the Ground Node

		Arguments:
			debug: (optional) log debugging data
	"""

	sender = imagezmq.ImageSender(connect_to='tcp://127.0.0.1:'+str(CommunicationUtils.CAM_PORT))
	logger.debug("Sending images to port: "+'tcp://127.0.0.1:'+str(CommunicationUtils.CAM_PORT))

	camNames = ["mainCam"]
	camCaps = [cv2.VideoCapture(0)]

	#for i in range(1,settings['numCams']):
	#	camNames.append("bkpCam"+str(i))
	#	camCaps.append(cv2.VideoCapture(i))
	numCams = len(camCaps)
	logger.debug('Cam names and Objects: '+str(camNames)+', '+str(camCaps))

	time.sleep(2.0)
	try:
		while execute['streamVideo']:
			for i in range(0,numCams):
				_, img = camCaps[i].read()
				try:
					sender.send_image(camNames[i], img)
				except:
					logger.warning("Invalid Image: "+str(img))
					time.sleep(1)
				if debug:
					logger.debug("Sent Image: "+str(img[:1][:1]))
	except Exception as e:
		logger.error("VideoStream Thread Exception Occurred: {}".format(e), exec_info=True)
	logger.debug("Stopped VideoStream")

def receiveData(debug=False):
	""" Recieves and processes JSON data from the Water Node
		
		Data will most likely contain motor data, and settings changes

		Arguments:
			debug: (optional) log debugging data
	"""

	HOST = '127.0.0.1'
	PORT = CommunicationUtils.CNTLR_PORT

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
	HOST = '127.0.0.1'
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
					"accel": {
						"x": 0,
						"y": 0,
						"z": 0,
					},
					"volts": 0,
					"amps": 0
				}
				sendQueue.put([sensors,"sensors",True,True])
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
	logger.info("Starting Water Node")
	logger.debug("Started all Threads")
	vidStreamThread = threading.Thread(target=sendVideoStreams, args=(verbose[0],),daemon=True)
	recvDataThread = threading.Thread(target=receiveData, args=(verbose[0],),daemon=True)
	sendDataThread = threading.Thread(target=sendData, args=(groundQueue,verbose[0],),daemon=True)
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
	CommunicationUtils.clearQueue(groundQueue)
	sys.exit()