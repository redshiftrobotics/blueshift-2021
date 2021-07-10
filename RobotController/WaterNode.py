'''
This file has both the Air and Earth nodes
'''
# Utility Imports
import sys
import os
import argparse
import subprocess

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
import ControllerUtils
from simple_pid import PID

# Settings Dict to keep track of editable settings for data processing
settings = {
	"numCams": 3,
    "maxCams": 3,
	"numMotors": 8,
	"minMotorSpeed": 0,
	"maxMotorSpeed": 180,
	"mainCameraResolution": {
		"x": 640,#1920,
		"y": 360,#1080
	},
	"bkpCameraResolution": {
		"x": 640,
		"y": 480
	},
	"v4l2QueueNum": 1
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

# IMU and PWM interface classes
IMU = HardwareUtils.IMUFusion()
SD = HardwareUtils.ServoDriver([(0, "WP120T"), (14, "T100"), (9, "T100"), (10, "T100"), (8, "T100"), (15, "T100"), (13, "T100"), (11, "T100"), (12, "T100")], frequency=330)
drivetrain_motor_mapping = [14, 9, 10, 8, 15, 13, 11, 12]
gripper_servo = 0

# Initialize ESC
SD.set_all_servos(0, only_type="T100")
time.sleep(2)

DC = ControllerUtils.DriveController(flip=[0,0,0,1,0,1,1,0])

mode = "user-control"
override = False

rot = {
	"x": {
		"Kp": 1/30,
		"Kd": 0,
		"Ki": 0
		},
	"y": {
		"Kp": 1/30,
		"Kd": 0,
		"Ki": 0
		},
	"z": {
		"Kp": 1/30,
		"Kd": 0,
		"Ki": 0
	}
}
xRotPID = PID(rot["x"]["Kp"], rot["x"]["Kd"], rot["x"]["Ki"], setpoint=0)
yRotPID = PID(rot["y"]["Kp"], rot["y"]["Kd"], rot["y"]["Ki"], setpoint=0)
zRotPID = PID(rot["z"]["Kp"], rot["z"]["Kd"], rot["z"]["Ki"], setpoint=0)

imu_state = IMU.get_full_state()

def stopAllThreads(callback=0):
	""" Stops all currently running threads
		
		Argument:
			callback: (optional) callback event
	"""

	execute['streamVideo'] = False
	execute['receiveData'] = False
	execute['sendData'] = False
	time.sleep(0.5)

def restartVideoStream():
	lock.acquire()
	try:
		restartCamStream = True
	except:
		pass
	finally:
		lock.release()		

def sendVideoStreams(debug=False):
	""" Sends video from each camera to the Earth Node

		Arguments:
			debug: (optional) log debugging data
	"""
	global restartCamStream

	# Initialize the ZMQ client
	sender = imagezmq.ImageSender(connect_to='tcp://'+ (CommunicationUtils.SIMPLE_EARTH_IP if simpleMode else CommunicationUtils.EARTH_IP) +':'+str(CommunicationUtils.CAM_PORT))

	# Initialize arrays to keep track of camera objects and names
	camNames = ["mainCam"] # Names of all of the cameras
	camCaps = [] # Video capture objects
	if not simpleMode:
		# Initialize a camera using the custom V4L2 Camera Driver
		camCaps = [v4l2_camera.Camera("/dev/video0", settings["mainCameraResolution"]["x"], settings["mainCameraResolution"]["y"], settings["v4l2QueueNum"])]
	else:
		# Initialize a camera using OpenCV
		camCaps = [cv2.VideoCapture(0)]
	
	# Automatically initialize the rest of the cameras

	# NOTE: UNCOMMENT LATER
	# These changes simulate the bandwidth necessary for three cameras by sending each frame three times, but only reading it once
	'''
	for i in range(1,settings['numCams']):

		# Add the camera name
		camNames.append("bkpCam"+str(i))
		if not simpleMode:
			# Add the camera object

			# This line is currently commented out because I only have one camera to test with so, for now, I just read data from that camera many times
			# camCaps.append(v4l2_camera.Camera("/dev/video"+str(i), settings["bkpCameraResolution"]["x"],settings["bkpCameraResolution"]["y"], settings["v4l2QueueNum"]))
			camCaps.append(camCaps[0])
		else:
			camCaps.append(camCaps[0])
	'''
	
	
	# Calculate the total number of camera
	numCams = len(camCaps)

	# Wait 2 seconds for the cameras to warm up
	time.sleep(2.0)

	while execute['streamVideo']:
		# Loop through each camera and stream its video
		for i in range(0,numCams):
			jpg_img = ""
			if not simpleMode:
				# Read a single frame (this is already jpg compressed)
				frame = camCaps[i].get_frame()
				# NOTE: UNCOMMENT LATER
				#sender.send_jpg(camNames[i]+"|"+str(frame.timestamp), frame.img)

				# Send the frame over ZMQ
				# The name of the camera is in the format [camera_name]|[timestamp] so that we can tell when the image was sent after it is recieved
				sender.send_jpg("mainCam"+"|"+str(frame.timestamp), frame.img)
				#sender.send_jpg("bkpCam1"+"|"+str(frame.timestamp), frame.img)
				#sender.send_jpg("bkpCam2"+"|"+str(frame.timestamp), frame.img)
				
			else:
				# Read a frame from the camera (This is uncompressed)
				_, img = camCaps[i].read()

				# Send it over ZMQ, the name follows the same formatting as before
				sender.send_image(camNames[i]+"|"+str(time.time()), img)
			
		# If we recieve the command to restart the camera stream, do so
		if restartCamStream:
				sender = imagezmq.ImageSender(connect_to='tcp://'+ (CommunicationUtils.SIMPLE_EARTH_IP if simpleMode else CommunicationUtils.EARTH_IP) +':'+str(CommunicationUtils.CAM_PORT))

				# Reset restartCamStream
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
	global SD
	global mode
	global override

	# Get the IP address and port of the earth node
	HOST = CommunicationUtils.SIMPLE_EARTH_IP if simpleMode else CommunicationUtils.EARTH_IP
	PORT = CommunicationUtils.CNTLR_PORT
	
	# Create the socket connection
	connected = True
	cntlr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	try:
		# Try to connect
		cntlr.connect((HOST, PORT))
		print("receiveData inital connection check succeded")
	except ConnectionRefusedError:
		connected = False
		print("receiveData inital connection check failed")
	
	while execute['receiveData']:
		try:
			# Recieve messages over the socket, each message is handled differently based on its tag and metatdata
			recv = CommunicationUtils.recvMsg(cntlr)
			#print(time.time() - recv['timestamp'], recv['tag'])
			if recv['tag'] == 'stateChange':
				if recv['data'] == 'close':
					stopAllThreads()
				elif recv['data'] == 'restartCamStream':
					restartCamStream = True
				elif recv['metadata'] == 'hold-angle':
					# Reset PID rotation controllers
					xRotPID.reset()
					yRotPID.reset()
					#zRotPID.reset()
					xRotPID.tunings = (rot["x"]["Kp"], rot["x"]["Kd"], rot["x"]["Ki"])
					yRotPID.tunings = (rot["y"]["Kp"], rot["y"]["Kd"], rot["y"]["Ki"])
					#zRotPID.tunings = (rot["Kp"], rot["Kd"], rot["Ki"])

					# Assuming the robot has been correctly calibrated, (0,0,0) should be upright
					xRotPID.setpoint = recv['data']['x']
					yRotPID.setpoint = recv['data']['y']
					#zRotPID.setpoint = stabilizeRot["z"]
					mode = "hold-angle"

				elif recv['metadata'] == 'override':
					override = recv['data']
				elif recv['metadata'] == 'stop-motors':
					mode = 'user-control'
				
				elif recv['metadata'] == 'stabilize':
					xRotPID.setpoint = recv['data']['x']
					yRotPID.setpoint = recv['data']['y']
                    # zRotPID.setpoint = recv['data']['z']
					mode = 'stabilize'
				

				print(recv, override, mode)

			if recv['tag'] == 'config':
					if recv['metadata'] == 'sync-time':
						# TODO: We should really be using subprocess here, because os.system is depricated, but I can't get subprocess working
						pass#os.system(f'sudo date --set="{ recv["data"] }"')
						#subprocess.run(f'sudo date --set="{ recv["data"] }"')
			elif recv['tag'] == 'settingChange':
				if recv['metadata'] == 'imuStraighten':
					IMU.set_offset(recv["data"])
			elif recv['tag'] == "motorData":
				if recv['metadata'] == "drivetrain":
					if time.time() - recv['timestamp'] < 0.1:
						speeds = [0]*6
						if (mode == "user-control" or override):
							speeds = DC.calcMotorValues(recv['data'][0],
														recv['data'][1],
														recv['data'][2],
														recv['data'][3],
														recv['data'][4],
														recv['data'][5])
						elif mode == 'hold-angle':
							xTgt = xRotPID(imu_state["imu"]["gyro"]["x"])
							yTgt = yRotPID(imu_state["imu"]["gyro"]["y"])

							speeds = DC.calcMotorValues(recv['data'][0],
														recv['data'][1],
														recv['data'][2],
														xTgt,
														yTgt,
														recv['data'][5])
						elif mode == 'stabilize':
							xTgt = xRotPID(imu_state["imu"]["gyro"]["x"])
							yTgt = yRotPID(imu_state["imu"]["gyro"]["y"])

							speeds = DC.calcMotorValues(recv['data'][0],
														recv['data'][1],
														recv['data'][2],
														xTgt,
														yTgt,
														recv['data'][5])


						#print(recv['data'])
						for loc,spd in enumerate(speeds):
							SD.set_servo(drivetrain_motor_mapping[loc], spd*0.5)
			elif recv['tag'] == "gripData":
				if recv['metadata'] == "arm-angle":
					if time.time() - recv['timestamp'] < 0.1:
						SD.move_servo(gripper_servo, recv['data'], 180, 20)
						#print(recv['data'])
						#pass

		# If we loose connection, try to reconnect
		except (OSError):
			print("receiveData connection lost")
			connected = False
			cntlr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			while (not connected) and execute['sendData']:
				try:
					cntlr.connect((HOST, PORT))
					connected = True
					print("receiveData successful reconnection")
				except ConnectionRefusedError:
					print("receiveData reconnect failed. trying in 2 seconds")
					time.sleep(2)
	# Close the socket connection
	cntlr.close()

def sendData(debug=False):
	""" Sends JSON data to the Water Node

		Data will most likely be sensor data from an IMU and voltage/amperage sensor

		Arguments:
			debug: (optional) log debugging data
	"""
	global IMU
	global imu_state

	# Get the IP address and port of the earth node
	HOST = CommunicationUtils.SIMPLE_EARTH_IP if simpleMode else CommunicationUtils.EARTH_IP
	PORT = CommunicationUtils.SNSR_PORT

	# Create the socket connection
	connected = True
	snsr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	try:
		# Try to connect
		snsr.connect((HOST, PORT))
		print("sendData inital connection check succeded")
	except ConnectionRefusedError:
		connected = False
		print("sendData inital connection check failed")
	
	lastMsgTime = time.time()
	
	while execute['sendData']:
		try:
			# Get gyro, accel readings
			sensors = IMU.get_full_state()

			imu_state = sensors
			
			# TODO: Update this with a proper sleep loop time managment system thing
			CommunicationUtils.sendMsg(snsr, CommunicationUtils.packet(tag="sensor",data=sensors))
			time.sleep(0.05)

		# If we loose connection, try to reconnect
		except (ConnectionResetError, BrokenPipeError):
			print("sendData connection lost")
			connected = False
			snsr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			while (not connected) and execute['sendData']:
				try:
					snsr.connect((HOST, PORT))
					connected = True
					print("sendData successful reconnection")
				except ConnectionRefusedError:
					print("sendData reconnect failed. trying in 2 seconds")
					time.sleep(2)
	# Close the socket connection
	snsr.close()

if( __name__ == "__main__"):
	# Setup Logging preferences
	verbose = [False,True]
	
	# Start all of the threads for communication
	vidStreamThread = threading.Thread(target=sendVideoStreams, args=(verbose[0],))
	recvDataThread = threading.Thread(target=receiveData, args=(verbose[0],))
	sendDataThread = threading.Thread(target=sendData, args=(verbose[0],))
	vidStreamThread.start()
	recvDataThread.start()
	sendDataThread.start()

	# We don't want the program to end uptil all of the threads are stopped
	while execute['streamVideo'] and execute['receiveData'] and execute['sendData']:
		time.sleep(0.1)
	recvDataThread.join()
	sendDataThread.join()
	vidStreamThread.join()
