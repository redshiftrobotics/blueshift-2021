'''
This is a script to test one dimensional perlin noise generation
It should eventually be integrated into the whole codebase for simulating fake data
'''

# Import necessary libraries
from noise import pnoise1
import time
import random

# Setup Perlin noise parameters
octaves = 1
start = time.time()

slow = 10
noiseRange = 1
y2Offset = random.randint(10,100)

# Loop forver while calculating perlin noise
while 1:
	x = float(-(time.time()-start))/float(slow)
	y1 = pnoise1(x, octaves) * float(noiseRange)
	y2 = pnoise1(x+y2Offset, octaves) * float(noiseRange)
	print(x,y1,y2)
	time.sleep(0.5)
