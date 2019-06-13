import sys
sys.path.insert(0, 'imagezmq/imagezmq')  # imagezmq.py is in ../imagezmq

# run this program on the Mac to display image streams from multiple RPis
import cv2
import imagezmq

image_hub = imagezmq.ImageHub()
while True:  # show streamed images until Ctrl-C
	rpi_name, image = image_hub.recv_image()
	print("recieved images")
	print(rpi_name)
	print(image[:1])
	cv2.imshow(rpi_name, image) # 1 window for each device
	cv2.waitKey(1)
	image_hub.send_reply(b'OK')