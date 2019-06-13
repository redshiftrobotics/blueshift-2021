import socket
import CommunicationUtils
import time
import glob
import cv2

HOST = '127.0.0.1'#'169.254.223.90'  # The server's hostname or IP address
PORT = 65432        # The port used by the server

wtr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,480)
width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
fps = cap.get(cv2.CAP_PROP_FPS)
print("W: "+str(width)+"  H: "+str(height))
print("FPS: "+str(fps))

try:
	wtr.connect((HOST, PORT))
	while 1:
		ret, frame = cap.read()
		encoded_img = CommunicationUtils.encode_img(frame)
		sent = CommunicationUtils.sendMsg(wtr,encoded_img,"image","None")
		## print("Sending: ",sent[:100],"...")
		## print("Length: ", sentLen)
		# time.sleep(1.0/(fps*1.8))

except Exception as e:
	print(e)
	wtr.close()