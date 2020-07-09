'''
This script tests communication over a TCP socket
'''

# Import necessary libraries
import socket

# Create a socket connection
HOST = '169.254.23.12'  # The server's hostname or IP address
PORT = 65432        # The port used by the server
wtr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


try:
	# Open the socket connection
	wtr.connect((HOST, PORT))
	# Send a message
	wtr.sendall('Hello, world'.encode())
	# Recieve a message
	data = wtr.recv(1024)
	print('Received', repr(data))

except:
	wtr.close()