# pylint: disable=C0103,R0904,C0301

import logging
import time

from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
import PyExpLabSys.drivers.pfeiffer_turbo_pump as tp
import credentials

port = 'serial/by-id/usb-FTDI_FT232R_USB_UART_A602SOEK-if00-port0'
mainpump = tp.TurboDriver(adress=1,port='/dev/' + port)
mainpump.start()

tui = tp.CursesTui(mainpump)
tui.daemon = True
tui.start()

reader = tp.TurboReader(mainpump)
reader.daemon = True
reader.start()

time.sleep(10) # Allow reader to make meaningfull moving avarage

rotation_logger = tp.TurboLogger(reader, 'rotation_speed', maximumtime=600)
rotation_logger.daemon = True
rotation_logger.start()

power_logger = tp.TurboLogger(reader, 'drive_power', maximumtime=600)
power_logger.daemon = True
power_logger.start()

current_logger = tp.TurboLogger(reader, 'drive_current', maximumtime=600)
current_logger.daemon = True
current_logger.start()

temp_electronics_logger = tp.TurboLogger(reader, 'temp_electronics', maximumtime=600)
temp_electronics_logger.daemon = True
temp_electronics_logger.start()

temp_bottom_logger = tp.TurboLogger(reader, 'temp_bottom', maximumtime=600)
temp_bottom_logger.daemon = True
temp_bottom_logger.start()

temp_bearings_logger = tp.TurboLogger(reader, 'temp_bearings', maximumtime=600)
temp_bearings_logger.daemon = True
temp_bearings_logger.start()

temp_motor_logger = tp.TurboLogger(reader, 'temp_motor', maximumtime=600)
temp_motor_logger.daemon = True
temp_motor_logger.start()

#livesocket = LiveSocket([chamber_turbo_speed', 'chamber_turbo_power'], 2)
#livesocket.start()

socket = DateDataPullSocket('microturboreader', ['current', 'speed'], timeouts=[1.0, 1.0], port=9000)
socket.start()

db_logger = ContinuousLogger(table='dateplots_microreactor', username=credentials.user, password=credentials.passwd, measurement_codenames=['mr_chamber_turbo_temp_motor', 'mr_chamber_turbo_current', 'mr_chamber_turbo_speed', 'mr_chamber_turbo_temp_bottom', 'mr_chamber_turbo_temp_bearings', 'mr_chamber_turbo_temp_electronics', 'mr_chamber_turbo_power'])
db_logger.start()
time.sleep(5)

while mainpump.running:
    time.sleep(0.1)
    ts = rotation_logger.read_value()
    power = power_logger.read_value()
    current = current_logger.read_value()
    temp_elec = temp_electronics_logger.read_value()
    temp_bottom = temp_bottom_logger.read_value()
    temp_bearings = temp_bearings_logger.read_value()
    temp_motor = temp_motor_logger.read_value()
    #livesocket.set_point_now('chamber_turbo_speed', ts)
    #socket.set_point_now('current', current)
    #socket.set_point_now('speed', ts)
    socket.set_point_now('current', rotation_logger.turboreader.turbo.status['drive_current'])
    socket.set_point_now('speed', rotation_logger.turboreader.turbo.status['rotation_speed'])

    if rotation_logger.trigged:
        db_logger.enqueue_point_now('mr_chamber_turbo_speed', ts)
        rotation_logger.trigged = False

    if power_logger.trigged:
        db_logger.enqueue_point_now('mr_chamber_turbo_power', power)
        power_logger.trigged = False

    if current_logger.trigged:
        db_logger.enqueue_point_now('mr_chamber_turbo_current', current)
        current_logger.trigged = False

    if temp_electronics_logger.trigged:
        db_logger.enqueue_point_now('mr_chamber_turbo_temp_electronics', temp_elec)
        temp_electronics_logger.trigged = False

    if temp_bottom_logger.trigged:
        db_logger.enqueue_point_now('mr_chamber_turbo_temp_bottom', temp_bottom)
        temp_bottom_logger.trigged = False

    if temp_bearings_logger.trigged:
        db_logger.enqueue_point_now('mr_chamber_turbo_temp_bearings', temp_bearings)
        temp_bearings_logger.trigged = False

    if temp_motor_logger.trigged:
        db_logger.enqueue_point_now('mr_chamber_turbo_temp_motor', temp_motor)
        temp_motor_logger.trigged = False
