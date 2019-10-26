### RUN THIS TO COMPILE THE LIBRARY: c++ -O3 -Wall -shared -std=c++11 -fPIC `python3 -m pybind11 --includes` webcam.cpp -o webcam`python3-config --extension-suffix` ###

from webcam import Camera
import cv2
import numpy as np
import io
from PIL import Image

c = Camera("/dev/video0",1920,1080)
for i in range(10):
    img = c.get_frame(1)
    #print(len(img))
    print(img)
    #print(bytearray(img))
    #try:
        #Image.open(io.BytesIO(img))
        #img_b = np.frombuffer(img)
        #print(img.decode("ISO-8859-1")) #"utf-8" "utf-16"
        #print(list(img))
        #cv2.imwrite("cam-" + str(i) + ".jpg",cv2.imdecode(np.array(list(img)),-1))
        #print(max(list(img)))
        #f = open("cam-" + str(i) + ".jpg", "wb")
        #f.write(img)
        #f.close()
        #print(cv2.imdecode(np.array(list(img)),1))
    #except Exception as e:
    #    print(e)
    #picture = Image.open(img_b)
    #print(cv2.imdecode(img_b,-1))