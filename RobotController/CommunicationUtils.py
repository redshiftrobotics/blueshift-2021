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
	msg = str(len(msg))+msg
	sckt.sendall(msg.encode())
	return msg

def recvMsg(conn):
	lengthMarker = b'|'
	msgLength = b''

	while(conn.recv(1, socket.MSG_PEEK)):
		data = conn.recv(1)
		if(data != lengthMarker):
			msgLength += data
		else:
			break
	recv = conn.recv(int(msgLength)-1)
	return recv

def encode_img(image):
	retval, bffr = cv2.imencode('.jpg', image)
	return base64.b64encode(bffr).decode("utf-8")