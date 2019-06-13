import json
import time
import socket
import base64
import cv2

def sendMsg(sckt,data,dataType,metadata):
	msg = "|"
	msg += "{"
	msg += '"dataType":"'+str(dataType)+'",'
	msg += '"data":"'+str(data)+'",'
	msg += '"timestamp":'+str(time.time())+','
	msg += '"metadata":"'+str(metadata)+'"'
	msg += "}"
	msgLen = len(msg)
	msg = str(msgLen)+msg
	sckt.sendall(msg.encode())
	return msg, msgLen

def recvMsg(conn):
	lengthMarker = b'|'
	msgLength = b''

	while(conn.recv(1, socket.MSG_PEEK)):
		data = conn.recv(1)
		if(data != lengthMarker):
			msgLength += data
		else:
			break

	iMsgLength = int(msgLength)
	while(len(conn.recv(iMsgLength, socket.MSG_PEEK))<iMsgLength):
		time.sleep(0.0001)
	recv = conn.recv(iMsgLength-1)
	return str(recv.decode()), iMsgLength

def encode_img(image):
	retval, bffr = cv2.imencode('.jpg', image)
	return base64.b64encode(bffr).decode("utf-8")