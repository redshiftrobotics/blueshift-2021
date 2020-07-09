'''
This script tests recieving images from a different computer over a ZMQ video stream
'''

# Import necessary libraries
import sys
sys.path.insert(0, 'imagezmq/imagezmq')  # imagezmq.py is in ../imagezmq
import cv2
import imagezmq

# Open the ZMQ server
image_hub = imagezmq.ImageHub()

while True:
	# Recive and display images from all clients
	rpi_name, image = image_hub.recv_image()
	print("recieved images")
	print(rpi_name)
	print(image[:1])
	cv2.imshow(rpi_name, image)
	cv2.waitKey(1)
	image_hub.send_reply(b'OK')