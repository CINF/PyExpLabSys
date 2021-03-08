import time

import numpy as np

from PIL import Image
from picamera import PiCamera

# HEIGHT must be multiplum of 32
# WIDTH must be multiplum of 16
HEIGHT = 1280
WIDTH = 720

# camera = PiCamera(resolution=(HEIGHT, WIDTH), framerate=30)

camera = PiCamera(
    resolution=(1280, 720),
    # framerate=Fraction(1, 6),
    framerate=1/6,
    sensor_mode=3
)
camera.awb_mode = 'off'
camera.awb_gains(1.0)

# camera.shutter_speed = 6000000
camera.shutter_speed = 6000

camera.iso = 400
time.sleep(0.2)  # Two seconds is a more conventional choice
# Now fix the values

camera.shutter_speed = camera.exposure_speed
camera.exposure_mode = 'off'
g = camera.awb_gains
camera.awb_mode = 'off'
camera.awb_gains = g


# First image
output = np.empty((WIDTH, HEIGHT, 3), dtype=np.uint8)
camera.capture(output, 'rgb')  
data = Image.fromarray(output)
data.save('first.png') 
first_intensity = np.mean(output) / 256

print('Change sample')
time.sleep(2)

# Second image
output = np.empty((WIDTH, HEIGHT, 3), dtype=np.uint8)
camera.capture(output, 'rgb')  
data = Image.fromarray(output)
data.save('second.png') 
second_intensity = np.mean(output) / 256

print('First: {}, Second: {}. Ratio: {}'.format(
    first_intensity,
    second_intensity,
    first_intensity / second_intensity
))
