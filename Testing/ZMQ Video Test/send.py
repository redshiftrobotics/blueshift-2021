# import imagezmq from parent directory
import sys
sys.path.insert(0, 'imagezmq/imagezmq')  # imagezmq.py is in ../imagezmq

import socket
import time
import cv2
import imagezmq

# use either of the formats below to specifiy address of display computer
# sender = imagezmq.ImageSender(connect_to='tcp://jeff-macbook:5555')
sender = imagezmq.ImageSender(connect_to='tcp://127.0.0.1:5555')

name = socket.gethostname()  # send RPi hostname with each image
cam = cv2.VideoCapture(0)
time.sleep(2.0)  # allow camera sensor to warm up
while True:  # send images as stream until Ctrl-C
    ret, image = cam.read()
    sender.send_image(name, image)
