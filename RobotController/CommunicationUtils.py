'''
This file utility code for all communication. That includes sockets, threads, packets, and more
'''

# Import necessary libraries
import simplejson as json
import time
import socket
import base64
import cv2
import time
import numpy as np
from copy import copy

# Hardcoded ports for communication
CAM_PORT = 6666
CNTLR_PORT = 6665
SNSR_PORT = 6664
AIR_PORT = 6663 # TODO: Update this to use port 80 for easier website access

# TODO: Figure out how to set custom link local IP Addresses and make these more human readable
# Ideally, when we switch to ElectronJS for the front end, we the IP address of the Earth Node will not matter
# This can be achieved for socket communication by just making the Earth Node connect to the Water Node (it is the other way around right now)
# It is a bit more complicated for ZMQ image streaming, because imagezmq requires the IP address of the host to be known
# (Though that also may not be an issue after we switch to using WebRTC or UDP via GStreamer on the Jetson NX)

# Hardcoded IP Addresses for communication
EARTH_IP = '169.254.61.199'
WATER_IP = '169.254.92.92'

SIMPLE_EARTH_IP = "localhost"

# Communication parameters
LENGTH_MARKER = b'|'

# TODO: Make all documentation consisitent with single or double quotes

def packet(tag="",data="",timestamp=False,metadata="",highPriority=False, copy_data=True):
	'''
	Generates a communication packet
	
	Arguments:
		tag: The tag of the packet. This defines where it will be sent
		data: This is the core data of the packet
		timestamp: The time the packet was created. If none is provided it will be set to the current time
		metadata: Any extra data about the packet
		highPriority: Whether this packet should have high priority. Currently, this does nothing, but there should eventually be some line skipping functionality
	
	Returns:
		The generated packet
	'''
	dataPacket = {
		"tag": tag,
		"data": copy(data) if copy_data else data,
		"timestamp": float(timestamp if timestamp else time.time()),
		"metadata": metadata,
		"highPriority": highPriority
	}
	return dataPacket

def sendMsg(sckt, pckt):
	""" 
	Send a JSON message through a socket

	Arguments:
		sckt: socket to send data through
		pckt: packet to be sent

	Returns:
		The sent message
	"""
	# Convert the json packet object into a string
	data = json.dumps(pckt)
	# Calculate its length
	msgLen = len(data)
	# Combine the length and the packet to make the message
	msg = str(msgLen)+LENGTH_MARKER.decode()+data
	# Send and return the message
	sckt.sendall(msg.encode())
	return msg

def recvMsg(conn,timeout=2):
	""" 
	Recieve a JSON message from a socket
	Messages should be formatted as [messge_length]|[message_contents]

	The usual method of serial or socket communication, is with predefined start and end characters.
	After a start character is recieved, one character at a time is read until an end character is reached.
	When large messages are being sent, this can become very slow.
	
	Because of that, we take a different approach.
	Each message sent is prefaced with the length of the message and a separator character.
	One character at a time is read until the separator character is reached.
	Then, the characters before the separator character are read, getting the length of the message.
	After we have the length of the message, we can read and return exactly that many characters.

	Arguments:
		conn: the socket to receive data through
		timeout: (optional) the maximum amount of time to wait before canceling

	Returns:
		The received message
	"""

	# TODO: Add the time out to the whole function
	# Right now it could theoretically wait for ever for the LENGTH_MARKER to be recieved

	# The implementation of message reading is not the cleanest
	# First, we peek into the socket until we see an end character
	# While doing this, we keep track of how many characters dep we are
	numChars = 2

	now = time.time()
	lastChar = conn.recv(numChars, socket.MSG_PEEK)[-1:]
	while(lastChar != LENGTH_MARKER):
		numChars += 1
		lastChar = conn.recv(numChars, socket.MSG_PEEK)[-1:]

	# After we find an end character, we find the total length of the message
	# That is equal to: the number of characters in the message itself + 1 (for the separator) + the lenght of the number of the number of characters in the message
	bMsgLength = conn.recv(numChars, socket.MSG_PEEK)
	iMsgLength = int(bMsgLength[:-1])
	iTotalLength = iMsgLength+len(bMsgLength)

	# We wait until either that many characters are available to be read, or time runs out
	while(len(conn.recv(iTotalLength, socket.MSG_PEEK))<iTotalLength):
		time.sleep(0.001)
		if (time.time()-now) > timeout:
			raise Exception("recvMsg Timeout of {} was reached".format(timeout))

	# Once enough characters are ready, we read and return the message
	conn.recv(numChars)
	recv = conn.recv(iMsgLength)
	return json.loads(str(recv.decode()))

def encodeImage(image):
    """ 
	Encodes an image in Base64

	Arguemnts:
		image: image to encode

	Returns:
		The Base64 encoded image
    """
    retval, bffr = cv2.imencode('.jpg', image)
    return bffr.tobytes()

def decodeImage(uri):
	'''
	Decodes an image from a base64 string

	Arguments:
		uri: the string to decode
	
	Returns:
		The decoded image
	'''
	nparr = np.fromstring(uri, np.uint8)
	img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
	return img

def clearQueue(qToClear, debug=False):
	'''
	Clears all the data out of a queue

	Arguments:
		qToClear: The queue to clear data out of
		debug (optional): Whether to log all of the data that is cleared from the queue
	
	Returns:
		Nothing
	'''

	if debug:
		print("Left in Queue:")
	while not qToClear.empty():
		if debug:
			print(qToClear.get())
		else:
			qToClear.get()
