### RUN THIS TO COMPILE THE LIBRARY: c++ -O3 -Wall -shared -std=c++11 -fPIC `python3 -m pybind11 --includes` webcam.cpp -o webcam`python3-config --extension-suffix` ###

from webcam import Camera
#import cv2
#import numpy as np
#import io
#from PIL import Image

c = Camera("/dev/video0",1920,1080)
for i in range(10):
    img = c.get_frame(1)
    print(img)
    print(len(img))
    #print(bytearray(img))
    #img_b = io.BytesIO(bytearray(img))
    #picture = Image.open(img_b)
    #print(cv2.imdecode(img,-1))