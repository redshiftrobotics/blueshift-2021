import json
import time
import socket

def sendMsg(sckt,data,dataType,metadata):
	msg = "<{"
	msg += '"'+str(dataType)+'":"'+str(data)+'",'
	msg += '"timestamp":'+str(time.time())+','
	msg += '"metadata":"'+str(metadata)+'"'
	msg += "}>"
	sckt.sendall(msg.encode())
	return msg

def recvMsg(conn):
	startMarker = "<"
	endMarker = ">"
	recvInProgress = False
	recv = ""

	while(conn.recv(1, socket.MSG_PEEK)):
		data = conn.recv(1).decode()
		if(recvInProgress):
			if(data != endMarker):
				recv += data
			else:
				recvInProgress = False
				break
		if(data == startMarker):
			recvInProgress = True
	return recv