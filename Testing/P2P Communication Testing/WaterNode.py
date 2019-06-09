from pyp2p.net import *
import time

#Setup Alice's p2p node.
water = Net(passive_bind="169.254.23.12", passive_port=44444, interface="eth0:2", node_type="passive", debug=1)
water.start()
water.bootstrap()
water.advertise()

#Event loop.
while 1:
    for con in water:
        for reply in con:
            print(reply)

    time.sleep(1)