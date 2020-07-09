'''
This script tests communication over a UDP socket
'''

# Import necessary libraries
import socket
import time

# Create a socket connection
UDP_IP = "169.254.23.12"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

while True:
	# Get an input message from the user
	v = input("Message:   ")

	# Send the message
	MESSAGE = v.encode()
	sock.sendto(MESSAGE, (UDP_IP,UDP_PORT))
