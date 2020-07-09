'''
This is a script that finds all of the controllers that are currently plugged in and prints out events from them
'''

# Import necessary libraries
from evdev import InputDevice, categorize, ecodes
import evdev

# Find all of the devices and allow the user to pick one
devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
for device in devices:
	print(device.path, device.name, device.phys)
choice = input("Pick a device: ")

# Read and log events from that device
try:
	device = devices[len(devices)-int(choice)-1].path
	dev = InputDevice(device)
	for event in dev.read_loop():
		if event:
			print(str(categorize(event))+" "+str(event.value))
except:
	print("Quitting...")
