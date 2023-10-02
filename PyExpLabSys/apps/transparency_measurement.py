import time

import numpy as np

from PIL import Image
from picamera import PiCamera

# HEIGHT must be multiplum of 32
# WIDTH must be multiplum of 16
# HEIGHT = 1280
# WIDTH = 720

# HEIGHT = 3280
# WIDTH = 2464

HEIGHT = 1632
WIDTH = 1232

# HEIGHT = 800
# WIDTH = 624

# camera = PiCamera(resolution=(HEIGHT, WIDTH), framerate=30)

camera = PiCamera(
    resolution=(HEIGHT, WIDTH),
    # framerate=Fraction(1, 6),
    framerate=5,
    sensor_mode=2,
)

time.sleep(1)

camera.exposure_mode = 'off'
camera.shutter_speed = 10000
camera.iso = 400
camera.awb_mode = 'off'
camera.awb_gains = (1.0, 1.0)
# First image

time.sleep(2)

target = 0.1

shutter = 1000
for i in range(0, 10):
    intensities = []
    camera.shutter_speed = shutter
    time.sleep(0.25)
    output = np.empty((WIDTH, HEIGHT, 3), dtype=np.uint8)
    # camera.capture(output, 'rgb', use_video_port=True)
    for i in range(0, 5):
        camera.capture(output, 'rgb', use_video_port=False)
        intensity = np.mean(output) / 256
        intensities.append(intensity)
    print(intensities)
    mean_int = np.mean(intensities)
    rel_int = target / mean_int
    shutter = int(shutter * rel_int)
    print('Rel Int: {:.3f}, Shutter: {}'.format(rel_int, shutter))

exit()


t = time.time()
output = np.empty((WIDTH, HEIGHT, 3), dtype=np.uint8)
# camera.capture(output, 'rgb', use_video_port=True)
camera.capture(output, 'rgb', use_video_port=False)
exposure_time = time.time() - t
print('Exposure time: {:.3f}'.format(exposure_time * 1000))
data = Image.fromarray(output)
data.save('first.png')
first_intensity = np.mean(output) / 256

camera.shutter_speed = 10000

print('Change sample')
# time.sleep(2)


# Second image
output = np.empty((WIDTH, HEIGHT, 3), dtype=np.uint8)
t = time.time()
# camera.capture(output, 'rgb', use_video_port=True)
camera.capture(output, 'rgb', use_video_port=False)
exposure_time = time.time() - t
print('Exposure time: {:.3f}ms'.format(exposure_time * 1000))

data = Image.fromarray(output)
data.save('second.png')
second_intensity = np.mean(output) / 256

print(
    'First: {}, Second: {}. Ratio: {}'.format(
        first_intensity, second_intensity, first_intensity / second_intensity
    )
)
