"Hint for implementation found at http://forum.arduino.cc/index.php?topic=285116.0 """

import smbus
import time

bus = smbus.SMBus(1)

DEVICE_ADDRESS = 0x6c

init = [0x0B, 0x00]
bus.write_i2c_block_data(DEVICE_ADDRESS, 0, init)


command = [0xD0, 0x40, 0x18, 0x06]
bus.write_i2c_block_data(DEVICE_ADDRESS, 0, command)
time.sleep(0.05)
command = [0xD0, 0x51, 0x2C]
bus.write_i2c_block_data(DEVICE_ADDRESS, 0, command)
time.sleep(0.1)
bus.write_byte(DEVICE_ADDRESS, 0x07)
time.sleep(0.2)
high = bus.read_byte(DEVICE_ADDRESS)
low = bus.read_byte(DEVICE_ADDRESS)
print 'High: ' + str(high) + ' Low: ' + str(low)

full_range = 1000.0 # I think....

value = high * 2**8 + low
print value
print (value - 1024) * full_range / 60000 - full_range/2
