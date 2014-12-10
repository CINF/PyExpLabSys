"""This file is responsible for measuring temeprature related to the coupled
reactor setup
"""

import time

from PyExpLabSys.common.sockets import DateDataPullSocket
import PyExpLabSys.drivers.omega_D6400 as D6400
from PyExpLabSys.common.utilities import get_logger
from PyExpLabSys.common.sockets import DateDataPullSocket
LOGGER = get_logger('coupled_reactor_temp')


class TemperatureLogger(object):

    def __init__(self):
        # Initialize omega driver
        LOGGER.info('Initialize omega d6400 driver')
        d6400_id = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWGRP0B-if00'\
            '-port0'
        self.d6400 = D6400.OmegaD6400(1, d6400_id)
        for channel in range(1, 8):
            LOGGER.info('Set range for channel {}'.format(channel))
            self.d6400.update_range_and_function(channel, action='tc',
                                                 fullrange='K')

        # Initialize socket
        name = 'Coupled reactor temperatures'
        self.codenames = {
            1: 'R1_temp',
            2: 'R1_sample_temp',
            3: 'R2_temp',
            4: 'R2_sample_temp',
            5: 'pro_inlet_temp',
            6: 'pro_d1_temp',
            7: 'pro_d2_temp',
            }
        codenames_list = [self.codenames[channel] for channel in range(1, 8)]
        self.socket = DateDataPullSocket(name, codenames_list, timeouts = 2.0)
        self.socket.start()

        # Measure initial values
        self.temperatures = {}
        for channel in range(1, 8):
            self.temperatures[channel] = self.d6400.read_value(channel)
            LOGGER.info('Get initial value {} for channel: {}'.format(
                    self.temperatures[channel], channel))
            self.socket.set_point_now(self.codenames[channel],
                                      self.temperatures[channel])

    def main(self):
        """Main meaurement loop"""
        while True:
            for channel in range(1, 8):
                self.temperatures[channel] = self.d6400.read_value(channel)
                LOGGER.info('Measured value {} for channel: {}'.format(
                        self.temperatures[channel], channel))
                self.socket.set_point_now(self.codenames[channel],
                                          self.temperatures[channel])
                

    def close(self):
        """Shut down the socket"""
        self.socket.stop()
        time.sleep(2)


if __name__ == '__main__':
    try:
        temperature_logger = TemperatureLogger()
        temperature_logger.main()
    except KeyboardInterrupt:
        temperature_logger.close()
