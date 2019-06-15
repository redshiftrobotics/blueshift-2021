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
	time.sleep(0.5)

def sendVideoStreams(debug=False):
	""" Sends video from each camera to the Ground Node

		Arguments:
			debug: (optional) log debugging data
	"""

	sender = imagezmq.ImageSender(connect_to='tcp://127.0.0.1:'+str(CommunicationUtils.CAM_PORT))
	logging.debug("Sending images to port: "+'tcp://127.0.0.1:'+str(CommunicationUtils.CAM_PORT))

	camNames = ["mainCam"]
	camCaps = [cv2.VideoCapture(0)]

	#for i in range(1,settings['numCams']):
	#	camNames.append("bkpCam"+str(i))
	#	camCaps.append(cv2.VideoCapture(i))
	numCams = len(camCaps)
	logging.debug('Cam names and Objects: '+str(camNames)+', '+str(camCaps))

	time.sleep(2.0)
	try:
		while execute['streamVideo']:
			for i in range(0,numCams):
				_, img = camCaps[i].read()
				try:
					sender.send_image(camNames[i], img)
				except:
					logging.warning("Invalid Image: "+str(img))
					time.sleep(1)
				if debug:
					logging.debug("Sent Image: "+str(img[:1][:1]))
	except Exception as e:
		logging.error("VideoStream Thread Exception Occurred",exec_info=True)
	logging.debug("Stopped VideoStream")

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
							logging.debug("Raw receive: "+str(recv))
							logging.debug("TtS: "+str(time.time()-float(j['timestamp'])))
					except Exception as e:
						logging.debug("Couldn't recieve data")
						stopAllThreads()

	except Exception as e:
		logging.error("Receive Thread Exception Occurred",exc_info=True)
	logging.debug("Stopped recvData")

def sendData(debug=False):
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
				try:
					sent = CommunicationUtils.sendMsg(snsr,sensors,"sensors","None")
				except Exception as e:
					logging.warning("Couldn't send data")
					stopAllThreads()

				if debug:
					time.sleep(1)
					logging.debug("Sending: "+str(sent))

	except Exception as e:
		logging.error("Send Thread Exception Occurred",exc_info=True)
	logging.debug("Stopped sendData")

if( __name__ == "__main__"):
	# Setup Logging preferences
	verbose = [False,True]

	for handler in logging.root.handlers[:]:
		logging.root.removeHandler(handler)
	logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.DEBUG)

	# Setup a callback to force stop the program
	keyboard.on_press_key("q", stopAllThreads, suppress=False)

	# Start each thread
	logging.info("Starting Water Node")
	logging.debug("Started all Threads")
	vidStreamThread = threading.Thread(target=sendVideoStreams, args=(verbose[0],),daemon=True)
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
	logging.info("Shutting Down Water Node")
	sys.exit()