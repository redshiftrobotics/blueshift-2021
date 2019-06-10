import socket
import CommunicationUtils
import json
import time
import asyncio
import websockets

HOST = '127.0.0.1'#'169.254.223.90'  # Standard loopback interface address (localhost)
PORT = 65432        # Port to listen on (non-privileged ports are > 1023)

gnd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    gnd.bind((HOST, PORT))
    gnd.listen()
    conn, addr = gnd.accept()
    print('Connected by', addr)

    async def stream(websocket, path):
        while True:
            data = CommunicationUtils.recvMsg(conn)
            ## print("Raw Data: ", data)
            j = json.loads(data)
            print(time.time()-float(j['timestamp']))
            await websocket.send(j['data']+str(int(time.time()*1000)))
            await asyncio.sleep(0.001)

    start_server = websockets.serve(stream, '127.0.0.1', 5678)

    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()

except Exception as e:
    print(e)
    gnd.close()