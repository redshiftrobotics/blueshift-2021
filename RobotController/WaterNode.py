import socket
import CommunicationUtils

HOST = '169.254.23.12'  # The server's hostname or IP address
PORT = 65432        # The port used by the server

wtr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
	wtr.connect((HOST, PORT))
	print("sent: "+CommunicationUtils.sendMsg(wtr,"Hello World!","text","None"))
	data = wtr.recv(1024)
	print('Received', str(data))
	wtr.close()

except Exception as e:
	print(e)
	wtr.close()