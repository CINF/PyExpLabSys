""" Simple driver for Keithley 2000 DMM """
from PyExpLabSys.drivers.scpi import SCPI


class Keithley2000(SCPI):
    """
    Simple driver for Keithley 2000 DMM
    """

    def __init__(self, interface, hostname='', device='',
                 baudrate=9600, gpib_address=None):
        if interface == 'serial':
            SCPI.__init__(self, interface=interface, device=device,
                          baudrate=baudrate, line_ending='\n')
            self.comm_dev.timeout = 2
            self.comm_dev.rtscts = False
            self.comm_dev.xonxoff = False
        if interface == 'gpib':
            SCPI.__init__(self, interface=interface, gpib_address=gpib_address)

    def set_bandwith(self, measurement='voltage:ac', bandwidth=None):
        scpi_cmd = 'SENSE:{}:DETector:BANDwidth'.format(measurement)
        if bandwidth is not None:
            DMM.scpi_comm(scpi_cmd + ' {}'.format(bandwidth))
        value_raw = DMM.scpi_comm(scpi_cmd + '?')
        value = float(value_raw)
        return value

    def set_range(self, value: float):
        """
        Set the measurement range of the device, 0 will indicate auto-range
        """
        if value > 1000:
            value = 1000
        if value < 0:
            value = 0
        if value == 0:
            self.scpi_comm(':SENSE:VOLT:DC:RANGE:AUTO ON')
            self.scpi_comm(':SENSE:VOLT:AC:RANGE:AUTO ON')
        else:
            self.scpi_comm(':SENSE:VOLT:DC:RANGE {:.5f}'.format(value))
            self.scpi_comm(':SENSE:VOLT:AC:RANGE {:.5f}'.format(value))

        actual_range_raw = self.scpi_comm(':SENSE:VOLTAGE:AC:RANGE?')
        actual_range = float(actual_range_raw)
        return actual_range

    def set_integration_time(self, nplc: float = None):
        """
        Set the measurement integration time
        """
        if nplc is not None:
            if nplc < 0.01:
                nplc = 0.01
            if nplc > 60:
                nplc = 60
            self.scpi_comm('SENSE:VOLTAGE:AC:NPLCYCLES {}'.format(nplc))
            # self.scpi_comm('SENSE:VOLTAGE:DC:NPLCYCLES {}'.format(nplc))
        current_nplc = float(self.scpi_comm('SENSE:VOLTAGE:AC:NPLCYCLES?'))
        return current_nplc

    def configure_measurement_type(self, measurement_type=None):
        """ Setup measurement type """
        if measurement_type is not None:
            # todo: Ensure type is an allow type!!!!
            self.scpi_comm(':CONFIGURE:{}'.format(measurement_type))
        actual = self.scpi_comm(':CONFIGURE?')
        return actual

    def read_ac_voltage(self):
        """ Read a voltage """
        raw = self.scpi_comm(':MEASURE:VOLTAGE:AC?')
        voltage = float(raw)
        return voltage

    def next_reading(self):
        """ Read next reading """
        t0 = time.time()
        while not self.measurement_available():
            time.sleep(0.001)
            if (time.time() - t0) > 10:
                # Todo: This is not good enough
                print('Keithley 2000 TIMEOUT!')
                break
        raw = self.scpi_comm(':DATA?')
        voltage = float(raw)
        return voltage

    def measurement_available(self):
        meas_event = int(self.scpi_comm('STATUS:MEASUREMENT:EVENT?'))
        mav_bit = 5
        mav = (meas_event & 2**mav_bit) == 2**mav_bit
        return mav


if __name__ == '__main__':
    import time

    GPIB = 16
    DMM = Keithley2000(interface='gpib', gpib_address=GPIB)

    # TODO! Something changes with the configuration when this
    # command is called, measurement is much slower and
    # NPLC command fails?!?!
    # print(DMM.configure_measurement_type('volt:ac'))

    DMM.set_range(0.1)
    print(DMM.set_integration_time(2))
    # print(DMM.set_bandwith())
    # print(DMM.set_integration_time(10))

    for i in range(0, 20):
        # time.sleep(0.05)
        t = time.time()
        # meas_event = DMM.scpi_comm('STATUS:MEASUREMENT:EVENT?')
        # print(bin(int(meas_event)))
        while not DMM.measurement_available():
            time.sleep(0.05)
        reading = DMM.next_reading()
        dt = time.time() - t
        print('Time: {:.2f}ms. AC {:.3f}uV'.format(dt * 1e3, reading * 1e6))
