'''
This script tests sending images to a different computer over a ZMQ video stream
'''

# Import necessary libraries
import sys
sys.path.insert(0, 'imagezmq/imagezmq')
import socket
import time
import cv2
import imagezmq

# Open a ZMQ connection with the server
sender = imagezmq.ImageSender(connect_to='tcp://127.0.0.1:5555')

# Get the name of the computer, this will be the id that images are sent with
name = socket.gethostname() + "2"
print(name)

# Open a camera device
cam = cv2.VideoCapture(0)
time.sleep(2.0)

while True:
    # Read images from the camera and send them over ZMQ
    ret, image = cam.read()
    sender.send_image(name, image)
