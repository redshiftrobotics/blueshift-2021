import socket
import time

UDP_IP = "169.254.23.12"#"169.254.210.42"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

while True:
	msg, addr = sock.recvfrom(1024)
	print(msg.decode())
