# pylint: disable=C0103,R0904,C0301

import logging
import time

from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataSocket
from PyExpLabSys.common.sockets import LiveSocket
import PyExpLabSys.drivers.pfeiffer_turbo_pump as tp
import credentials

port = 'serial/by-id/usb-FTDI_FT232R_USB_UART_AH01G9H4-if00-port0'
mainpump = tp.TurboDriver(adress=2,port='/dev/' + port)
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

# Todo: change port number
#livesocket = LiveSocket([chamber_turbo_speed', 'chamber_turbo_power'], 2)
#livesocket.start()

db_logger = ContinuousLogger(table='dateplots_mgw', username=credentials.user, password=credentials.passwd, measurement_codenames=['mgw_chamber_turbo_speed', 'mgw_chamber_turbo_power', 'mgw_chamber_turbo_temp_motor', 'mgw_chamber_turbo_temp_bottom', 'mgw_chamber_turbo_temp_bearings', 'mgw_chamber_turbo_temp_electronics', 'mgw_chamber_turbo_current'])
db_logger.start()
time.sleep(5)

while mainpump.running:
    ts = rotation_logger.read_value()
    power = power_logger.read_value()
    current = current_logger.read_value()
    temp_elec = temp_electronics_logger.read_value()
    temp_bottom = temp_bottom_logger.read_value()
    temp_bearings = temp_bearings_logger.read_value()
    temp_motor = temp_motor_logger.read_value()
    #livesocket.set_point_now('chamber_turbo_speed', ts)

    if rotation_logger.trigged:
        db_logger.enqueue_point_now('mgw_chamber_turbo_speed', ts)
        rotation_logger.trigged = False

    if power_logger.trigged:
        db_logger.enqueue_point_now('mgw_chamber_turbo_power', power)
        power_logger.trigged = False

    if current_logger.trigged:
        db_logger.enqueue_point_now('mgw_chamber_turbo_current', current)
        current_logger.trigged = False

    if temp_electronics_logger.trigged:
        db_logger.enqueue_point_now('mgw_chamber_turbo_temp_electronics', temp_elec)
        temp_electronics_logger.trigged = False

    if temp_bottom_logger.trigged:
        db_logger.enqueue_point_now('mgw_chamber_turbo_temp_bottom', temp_bottom)
        temp_bottom_logger.trigged = False

    if temp_bearings_logger.trigged:
        db_logger.enqueue_point_now('mgw_chamber_turbo_temp_bearings', temp_bearings)
        temp_bearings_logger.trigged = False

    if temp_motor_logger.trigged:
        db_logger.enqueue_point_now('mgw_chamber_turbo_temp_motor', temp_motor)
        temp_motor_logger.trigged = False

