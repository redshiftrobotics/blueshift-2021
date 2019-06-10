import socket
import CommunicationUtils

HOST = '169.254.23.12'  # Standard loopback interface address (localhost)
PORT = 65432        # Port to listen on (non-privileged ports are > 1023)

gnd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    gnd.bind((HOST, PORT))
    gnd.listen()
    conn, addr = gnd.accept()
    print('Connected by', addr)
    data = CommunicationUtils.recvMsg(conn)
    conn.sendall(data.encode())
    gnd.close()

except Exception as e:
    print(e)
    gnd.close()