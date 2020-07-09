'''
This script tests streaming from a camera to a website over websockets
This is a bad solution compared to doing it with flask, the code is messier and it is slower
'''

# Import necessary libraries
import asyncio
import websockets
import base64
import glob
import cv2
import numpy as np
import time

try:
	# Initialize a camera
	cap = cv2.VideoCapture(0)
	width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
	height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
	fps = cap.get(cv2.CAP_PROP_FPS)
	print("W: "+str(width)+"  H: "+str(height))
	print("FPS: "+str(fps))

	ret, frame = cap.read()

	# Stream images from the camera to a website using websockets
	def encode_img(image):
		retval, bffr = cv2.imencode('.jpg', image)
		return base64.b64encode(bffr).decode("utf-8") 

	async def stream(websocket, path):
		global counter
		while True:
			ret, frame = cap.read()
			encoded_img = encode_img(frame)
			await websocket.send(encoded_img+str(int(time.time()*1000)))
			await asyncio.sleep(0.001)

	start_server = websockets.serve(stream, '127.0.0.1', 5678)

	asyncio.get_event_loop().run_until_complete(start_server)
	asyncio.get_event_loop().run_forever()

except:
	cap.release()