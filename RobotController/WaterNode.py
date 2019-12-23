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
from pythonjsonlogger import jsonslogger
'''

# Imports for Threading
import threading
from queue import Queue

# Imports for Video Streaming
sys.path.insert(0, 'imagezmq/imagezmq')

import cv2
if not simpleMode:
	import v4l2_camera
import imagezmq
import numpy as np

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
	"mainCameraResolution": {
		"x": 1280,
		"y": 720
	},
	"bkpCameraResolution": {
		"x": 640,
		"y": 480
	},
	"v4l2QueueNum": 4,
}

# Dict to stop threads
execute = {
	"streamVideo": True,
	"sendData": True,
	"receiveData": True
}


# Queue, Logger, and Class for Multithreaded Logging Communication
lock = threading.Lock()
restartCamStream = False
earthQueue = Queue(0)

'''
class nodeHandler(logging.Handler):
	def emit(self, record):
		global earthQueue

		logEntry = self.format(record)
		earthQueue.put([json.loads(logEntry),"log",False,False])

logger = logging.getLogger("WaterNode")
'''

def stopAllThreads(callback=0):
	""" Stops all currently running threads
		
		Argument:
			callback: (optional) callback event
	"""

	execute['streamVideo'] = False
	execute['receiveData'] = False
	execute['sendData'] = False
	'''
	logger.debug("Stopping Threads")
	'''
	time.sleep(0.5)

def sendVideoStreams(debug=False):
	""" Sends video from each camera to the Earth Node

		Arguments:
			debug: (optional) log debugging data
	"""
	global restartCamStream
	sender = imagezmq.ImageSender(connect_to='tcp://'+ (CommunicationUtils.SIMPLE_EARTH_IP if simpleMode else CommunicationUtils.EARTH_IP) +':'+str(CommunicationUtils.CAM_PORT))
	'''
	logger.debug("Sending images to port: "+'tcp://'+CommunicationUtils.SIMPLE_EARTH_IP if simpleMode else CommunicationUtils.EARTH_IP+':'+str(CommunicationUtils.CAM_PORT))
	'''

	camNames = ["mainCam"]
	camCaps = []
	if not simpleMode:
		camCaps = [v4l2_camera.Camera("/dev/video0", settings["mainCameraResolution"]["x"], settings["mainCameraResolution"]["y"], settings["v4l2QueueNum"])]
	else:
		camCaps = [cv2.VideoCapture(0)]

	for i in range(1,settings['numCams']):
		camNames.append("bkpCam"+str(i))
		if not simpleMode:
			camCaps.append(camCaps[0]) #v4l2_camera.Camera("/dev/video"+str(i), settings["bkpCameraResolution"]["x"],settings["bkpCameraResolution"]["y"], settings["v4l2QueueNum"])) ### UPDATE LATER TO USE ADDITIONAL CAMERAS
		else:
			camCaps.append(camCaps[0])
	numCams = len(camCaps)
	'''
	logger.debug('Cam names and Objects: '+str(camNames)+', '+str(camCaps))
	'''

	time.sleep(2.0)
	while execute['streamVideo']:
		for i in range(0,numCams):
			jpg_img = ""
			if not simpleMode:
				jpg_img = camCaps[i].get_frame()
				sender.send_jpg(camNames[i]+"|"+str(time.time()), jpg_img)
			else:
				_, img = camCaps[i].read()
				sender.send_image(camNames[i]+"|"+str(time.time()), img)
			'''
			if debug:
				logger.debug("Sent Image: "+str(jpg_img))
			'''
		if restartCamStream:
				sender = imagezmq.ImageSender(connect_to='tcp://'+ (CommunicationUtils.SIMPLE_EARTH_IP if simpleMode else CommunicationUtils.EARTH_IP) +':'+str(CommunicationUtils.CAM_PORT))
				lock.acquire()
				try:
					restartCamStream = False
				except:
					pass
				finally:
					lock.release()

def receiveData(debug=False):
	""" Recieves and processes JSON data from the Water Node
		
		Data will most likely contain motor data, and settings changes

		Arguments:
			debug: (optional) log debugging data
	"""
	global restartCamStream

	SD = HardwareUtils.ServoDriver(enumerate(["T100"]*8))

	HOST = CommunicationUtils.SIMPLE_EARTH_IP if simpleMode else CommunicationUtils.EARTH_IP
	PORT = CommunicationUtils.CNTLR_PORT
	
	connected = True
	cntlr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	try:
		cntlr.connect((HOST, PORT))
	except ConnectionRefusedError:
		connected = False
	
	while execute['receiveData']:
		try:
			recv = CommunicationUtils.recvMsg(cntlr)
			if recv['tag'] == 'stateChange':
				if recv['data'] == 'close':
					stopAllThreads()
				if recv['data'] == 'restartCamStream':
					lock.acquire()
					try:
						restartCamStream = True
					except:
						pass
					finally:
						lock.release()
					
			
			elif recv['tag'] == "motorData":
				for loc,spd in enumerate(recv['data']):
					SD.set_servo(loc,spd)


			'''
			if debug:
				logger.debug("Raw receive: "+str(recv))
				logger.debug("TtS: "+str(time.time()-float(j['timestamp'])))
			'''
		except (OSError, KeyboardInterrupt):
			connected = False
			cntlr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			while (not connected) and execute['sendData']:
				try:
					cntlr.connect((HOST, PORT))
					connected = True
				except ConnectionRefusedError:
					time.sleep(2)
	cntlr.close()

	'''
		logger.error("Receive Thread Exception Occurred", exc_info=True)
	logger.debug("Stopped recvData")
	'''

def sendData(sendQueue,debug=False):
	""" Sends JSON data to the Water Node

		Data will most likely be sensor data from an IMU and voltage/amperage sensor

		Arguments:
			debug: (optional) log debugging data
	"""

	IMU = HardwareUtils.IMUFusion()

	HOST = CommunicationUtils.SIMPLE_EARTH_IP if simpleMode else CommunicationUtils.EARTH_IP
	PORT = CommunicationUtils.SNSR_PORT

	connected = True
	snsr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	try:
		snsr.connect((HOST, PORT))
	except ConnectionRefusedError:
		connected = False
	
	while execute['sendData']:
		try:
			# Get gyro, accel readings
			sensors = IMU.get_full_state()
			sendQueue.put(CommunicationUtils.packet(tag="sensor",data=sensors,timestamp=time.time()))
			time.sleep(1.0/100.0)
			while not sendQueue.empty():
				toSend = sendQueue.get()
				sent = CommunicationUtils.sendMsg(snsr,toSend)
				'''
				if debug:
					logger.debug("Sending: "+str(sent))
				'''

				'''
					logger.warning("Couldn't send data: {}".format(e), exc_info=True)
				'''
		except (BrokenPipeError, KeyboardInterrupt):
			connected = False
			snsr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			while (not connected) and execute['sendData']:
				try:
					snsr.connect((HOST, PORT))
					connected = True
				except ConnectionRefusedError:
					time.sleep(2)
	snsr.close()
	'''
		logger.error("Send Thread Exception Occurred: {}".format(e), exc_info=True)
	logger.debug("Stopped sendData")
	'''

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

	# Start each thread
	logger.info("Starting Water Node")
	logger.debug("Started all Threads")
	'''
	vidStreamThread = threading.Thread(target=sendVideoStreams, args=(verbose[0],))
	recvDataThread = threading.Thread(target=receiveData, args=(verbose[0],))
	sendDataThread = threading.Thread(target=sendData, args=(earthQueue,verbose[0],))
	vidStreamThread.start()
	recvDataThread.start()
	sendDataThread.start()

	# Begin the Shutdown
	while execute['streamVideo'] and execute['receiveData'] and execute['sendData']:
		time.sleep(0.1)
	recvDataThread.join()
	sendDataThread.join()
	vidStreamThread.join()
	'''
	logger.debug("Stopped all Threads")
	logger.info("Shutting Down Water Node")
	CommunicationUtils.clearQueue(earthQueue)
	'''