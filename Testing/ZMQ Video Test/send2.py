# import imagezmq from parent directory
import sys
sys.path.insert(0, 'imagezmq/imagezmq')

import socket
import time
import cv2
import imagezmq

sender = imagezmq.ImageSender(connect_to='tcp://127.0.0.1:5555')

name = socket.gethostname()+"2"  # send RPi hostname with each image
print(name)
cam = cv2.VideoCapture(0)
time.sleep(2.0)  # allow camera sensor to warm up
while True:  # send images as stream until Ctrl-C
    ret, image = cam.read()
    sender.send_image(name, image)
