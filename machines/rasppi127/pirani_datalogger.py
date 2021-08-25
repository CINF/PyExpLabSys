# -*- coding: utf-8 -*-
import time
from drivers import VPM5
from sockets import pirani_socket

VPM = VPM5('/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FT4UQMI8-if00-port0')

#Pull socket
data_sock = pirani_socket()

print(VPM.Qconfig())

try:
    while True:
        try:
            pressure = VPM.read_pressure()
            temperature = VPM.read_temperature()
            print(str(pressure)+', '+str(temperature))
            data_sock.set_point_now('pressure', [pressure])
            data_sock.set_point_now('temperature', [temperature])
        except:
            print('an error occured')
            time.sleep(0.1)
            continue
except KeyboardInterrupt:
    data_sock.stop() #This will free up the port again
