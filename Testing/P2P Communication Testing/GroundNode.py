from pyp2p.net import *

#Setup Bob's p2p node.
ground = Net(passive_bind="169.254.210.42", passive_port=44445, interface="eth0:1", node_type="passive", debug=1)
ground.start()
ground.bootstrap()
ground.advertise()

#Event loop.
while 1:
    for con in ground:
        con.send_line("test")

    time.sleep(1)