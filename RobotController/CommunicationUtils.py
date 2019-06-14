import json
import time
import socket
import base64
import cv2
import time
import logging

CAM_PORT = 5555
CNTLR_PORT = 5554
SNSR_PORT = 5553

def sendMsg(sckt,data,dataType,metadata,isString=True):
	""" Send a JSON message through a socket

		Arguments:
			sckt: socket to send data through
			data: data to be sent
			dataType: type of data to be sent
			metadata: extra data to be sent
			isString: (optiona) whether the data is a string

		Returns:
			The sent message
	"""
	msg = "|"
	msg += "{"
	msg += '"dataType":"'+str(dataType)+'",'
	if isString:
		msg += '"data":"'+str(data)+'",'
	else:
		msg += '"data":'+str(data)+','
	msg += '"timestamp":'+str(time.time())+','
	msg += '"metadata":"'+str(metadata)+'"'
	msg += "}"
	msgLen = len(msg)
	msg = str(msgLen)+msg
	sckt.sendall(msg.encode())
	return msg

def recvMsg(conn,timeout=2):
	""" Recieve a JSON message from a socket

		Messages should be formatted as msgLength|messageContents

		Arguments:
			conn: the socket to receive data through
			timeout: (optional) the maximum amount of time to wait before canceling

		Returns:
			The received message
	"""
	lengthMarker = b'|'
	numChars = 2

	now = time.time()
	lastChar = conn.recv(numChars, socket.MSG_PEEK)[-1:]
	while(lastChar != lengthMarker):
		numChars += 1
		lastChar = conn.recv(numChars, socket.MSG_PEEK)[-1:]

	bMsgLength = conn.recv(numChars, socket.MSG_PEEK)
	iMsgLength = int(bMsgLength[:-1])
	iTotalLength = iMsgLength+len(bMsgLength)
	while(len(conn.recv(iTotalLength, socket.MSG_PEEK))<iTotalLength):
		time.sleep(0.001)
		if (time.time()-now) > timeout:
			raise Exception("recvMsg Timeout of {} was reached".format(timeout))

	conn.recv(numChars)
	recv = conn.recv(iMsgLength-1)
	return str(recv.decode())

def closeSocket(sckt):
	""" Cleanly close a socket connection

		Starts by sending a shutdown JSON message through the socket

		Arguments:
			sckt: socket to close
	"""
	try:
		sendMsg(sckt,"closing","connInfo","None")
		sckt.shutdown(socket.SHUT_WR)
		sckt.close()
	except:
		pass

def encode_img(image):
	""" Encodes an image in Base64

		Arguemnts:
			image: image to encode

		Returns:
			The Base64 encoded image
	"""
	retval, bffr = cv2.imencode('.jpg', image)
	return base64.b64encode(bffr).decode("utf-8")