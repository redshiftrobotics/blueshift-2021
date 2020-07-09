'''
This script tests communication over a UDP socket
'''

# Import necessary libraries
import socket
import time

# Create a socket connection
UDP_IP = "169.254.23.12"#"169.254.210.42"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

while True:
	# Recieve messages
	msg, addr = sock.recvfrom(1024)
	print(msg.decode())
