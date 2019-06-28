from evdev import InputDevice, categorize, ecodes
import evdev

devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
for device in devices:
	print(device.path, device.name, device.phys)

choice = input("Pick a device: ")

try:
	device = devices[len(devices)-int(choice)-1].path
	dev = InputDevice(device)
	for event in dev.read_loop():
		if event.type == ecodes.EV_KEY:
			print(str(categorize(event))+" "+str(event.value))
except:
	print("Quitting...")
