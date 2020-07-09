# This is a bash script that evaluates different image compression methods in Python.

SETUP="
import cv2
import sys
from PIL import Image
sys.path.insert(0,'../../RobotController')
from CommunicationUtils import compressImage

img = cv2.imread('/home/pi/Downloads/test.png')
quality=10
"

echo "PIL Compression Test"
python -m timeit -s "$SETUP" "i = Image.fromarray(img); compressImage(i,quality=quality)"

echo "CV2 Compression Test"
python -m timeit -s "$SETUP" "cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])"
