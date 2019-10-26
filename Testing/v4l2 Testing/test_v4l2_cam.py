from v4l2_camera import Camera
import cv2
import numpy as np
import time
#import io
#from PIL import Image

c = Camera("/dev/video0",1920,1080,4)

now = time.time()
for i in range(10):
    img = c.get_frame()
    #print(len(img))
    #print(img)
    #cv2.imwrite("cam-" + str(i) + ".jpg",cv2.imdecode(np.array(list(img)),-1))
print("took",time.time()-now,"total")
print(10/(time.time()-now),"fps")