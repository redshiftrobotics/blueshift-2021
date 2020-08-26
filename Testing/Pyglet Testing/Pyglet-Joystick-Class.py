import pyglet
import threading
import time

class Joystick:
    
    def __init__(self, device_number, threshold= 0.001):
        self.threshold_value = threshold
        def setup_joystick(device_number,joystick_press,joystick_release, joystick_axis, joystick_Dpad ):
            import pyglet

            joysticks = pyglet.input.get_joysticks()
            joystick = joysticks[device_number]
            joystick.on_joybutton_press = joystick_press
            joystick.on_joybutton_release = joystick_release
            joystick.on_joyaxis_motion = joystick_axis
            joystick.on_joyhat_motion = joystick_Dpad
            joystick.open()
            pyglet.app.run()
        
        self.run = threading.Thread(target=setup_joystick,args=(device_number,self._joystick_press, self._joystick_release, self._joystick_axis, self._joystick_Dpad),daemon=True)
        self.run.start()
        
        self.left = {
            "stick": {
                "x": 0,
                "y": 0,
                "button": 0
            },
            "bumper": 0,
            "trigger": 0
        }
        self.right = {
            "stick": {
                "x": 0,
                "y": 0,
                "button": 0
            },
            "bumper": 0,
            "trigger": 0
        }
        self.d_pad = {
            "x": 0,
            "y": 0
        }
        self.buttons = {
            "back": 0,
            "start": 0,
            "home": 0,
            "a": 0,
            "b": 0,
            "x": 0,
            "y": 0
        }


    def _joystick_press(self,joystick, button):
      
        if button == 2:
            self.buttons['x'] = 1
        if button == 1:
            self.buttons['b'] = 1
        if button == 0:
            self.buttons['a'] = 1
        if button == 3:
            self.buttons['y'] = 1
        if button == 4:
            self.left['bumper'] = 1
        if button == 5:
            self.right['bumper'] = 1
        
    def _joystick_release(self, joystick, button):
        if button == 2:
            self.buttons['x'] = 0
        if button == 1:
            self.buttons['b'] = 0
        if button == 0:
            self.buttons['a'] = 0
        if button == 3:
            self.buttons['y'] = 0
        if button == 4:
            self.left['bumper'] = 1
        if button == 5:
            self.right['bumper'] = 1
        
    def threshold(self, value, threshold):
        if abs(value) < threshold:
            return 0.0
        return value


    def _joystick_axis(self,joystick, axis, value):
        
        value = self.threshold(value, self.threshold_value)
        
        
        if axis == 'rx':
            self.right['stick']['x'] = value
            
        if axis == 'ry':
            self.right['stick' ]['y']= value
            
        if axis == 'x':
            self.left['stick']['x'] = value
            
        if axis == 'y':
            self.left['stick' ]['y']= value
        if axis == 'z':
            if value > 0:
                self.left['trigger'] = value
            if value < 0:
                self.right['trigger'] = abs(value)

    def _joystick_Dpad(self, joystick, hat_x, hat_y):
        self.d_pad['x'] = hat_x 
        self.d_pad['y'] = hat_y 
        
  
joystick_class = Joystick(1)
while True:
    time.sleep(1)
    
