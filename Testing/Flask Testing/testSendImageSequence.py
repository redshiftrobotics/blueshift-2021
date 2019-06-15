import base64
import glob
import cv2
from flask import Flask, render_template, Response
import time

app = Flask(__name__)


counter = 0
images = []

for img in glob.glob("images/*.png"):
    n = cv2.imread(img)
    images.append(n)

print("loaded images")

@app.route('/')
def index():
    return render_template('index.html')

def gen():
    global counter
    while True:
        encoded_img = encode_img(images[counter%len(images)])
        counter += 1
        time.sleep(0.001)
        tosend = (b'--frame\r\n'+b'Content-Type: image/jpeg\r\n\r\n' + encoded_img + b'\r\n')
        yield tosend

@app.route('/video_feed')
def video_feed():
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def encode_img(image):
	retval, bffr = cv2.imencode('.jpg', image)
	return bffr.tobytes()

if __name__ == '__main__':
    app.run(host='127.0.0.1', debug=True)