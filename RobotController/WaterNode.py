import socket
import CommunicationUtils
import time
import glob
import cv2

HOST = '127.0.0.1'#'169.254.223.90'  # The server's hostname or IP address
PORT = 65432        # The port used by the server

wtr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

counter = 0
images = []

for img in glob.glob("images/*.png"):
    n = cv2.imread(img)
    images.append(n)

print("loaded images")

try:
	wtr.connect((HOST, PORT))
	while 1:
		encoded_img = CommunicationUtils.encode_img(images[counter%len(images)])
		counter += 1
		sent = CommunicationUtils.sendMsg(wtr,encoded_img,"image","None")
		print("Sending: ",sent)
		print("Length: ", len(sent))

except Exception as e:
	print(e)
	wtr.close()