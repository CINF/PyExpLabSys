from __future__ import print_function

from time import time

from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.drivers.epimax import PVCi


def measure_and_report(pvci, live_socket):
    values = pvci.get_fields('common')
    live_socket.set_point_now('thetaprobe_load_lock_pirani', values['slot_a_value_1'])
    live_socket.set_point_now('thetaprobe_pressure_main_ig', values['ion_gauge_1_pressure'])
    live_socket.set_point_now('thetaprobe_chamber_temperature', values['slot_b_value_1'])
    print(values)


def main():
    pvci = PVCi('/dev/serial/by-id/'
                'usb-FTDI_USB-RS485_Cable_FTY3M2GN-if00-port0')
    codenames = ['thetaprobe_pressure_main_ig', 'thetaprobe_load_lock_pirani',
                 'thetaprobe_chamber_temperature']
    live_socket = LiveSocket('thetaprobe_pvci', codenames, sane_interval=0.5)
    live_socket.start()

    try:
        while True:
            measure_and_report(pvci, live_socket)
    except KeyboardInterrupt:
        pvci.close()
        live_socket.stop()

main()
