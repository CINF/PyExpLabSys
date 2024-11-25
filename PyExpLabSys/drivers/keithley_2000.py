""" Simple driver for Keithley 2000 DMM """
import time

import pyvisa


class Keithley2000:
    """
    Simple driver for Keithley 2000 DMM
    """

    def __init__(self, interface, device='', baudrate=9600, gpib_address=None):
        rm = pyvisa.ResourceManager('@py')
        if interface == 'serial':
            conn_string = 'ASRL{}::INSTR'.format(device)
            self.instr = rm.open_resource(conn_string)
            self.instr.set_visa_attribute(
                pyvisa.constants.VI_ATTR_ASRL_FLOW_CNTRL,
                pyvisa.constants.VI_ASRL_FLOW_XON_XOFF,
            )
            self.instr.read_termination = '\n'
            self.instr.write_termination = '\n'
            self.instr.baud_rate = baudrate
        if interface == 'gpib':
            pass

    def set_bandwith(self, measurement='voltage:ac', bandwidth=None):
        scpi_cmd = 'SENSE:{}:DETector:BANDwidth'.format(measurement)
        if bandwidth is not None:
            self.instr.write(scpi_cmd + ' {}'.format(bandwidth))
        value_raw = self.instr.query(scpi_cmd + '?')
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
            self.instr.write(':SENSE:VOLT:DC:RANGE:AUTO ON')
            self.instr.write(':SENSE:VOLT:AC:RANGE:AUTO ON')
        else:
            self.instr.write(':SENSE:VOLT:DC:RANGE {:.5f}'.format(value))
            self.instr.write(':SENSE:VOLT:AC:RANGE {:.5f}'.format(value))
        # The instrument cannot process this infinitiely fast and might end up
        # lacking behind and filling up buffers - wait a little while to prevent this
        # time.sleep(0.4)
        actual_range_raw = self.instr.query(':SENSE:VOLTAGE:AC:RANGE?')
        actual_range = float(actual_range_raw)
        return actual_range

    def set_integration_time(self, nplc: float = None):
        """
        Set the measurement integration time
        """

        if 'AC' in self.configure_measurement_type():
            set_msg = 'SENSE:VOLTAGE:AC:NPLCYCLES {}'
            read_msg = 'SENSE:VOLTAGE:AC:NPLCYCLES?'
        else:
            set_msg = 'SENSE:VOLTAGE:DC:NPLCYCLES {}'
            read_msg = 'SENSE:VOLTAGE:DC:NPLCYCLES?'

        if nplc is not None:
            if nplc < 0.01:
                nplc = 0.01
            if nplc > 60:
                nplc = 60
            self.instr.write(set_msg.format(nplc))
        current_nplc = float(self.instr.query(read_msg))
        return current_nplc

    def configure_measurement_type(self, measurement_type=None):
        """Setup measurement type"""
        if measurement_type is not None:
            # todo: Ensure type is an allow type!!!!
            self.instr.write(':CONFIGURE:{}'.format(measurement_type))
        actual = self.instr.query(':CONFIGURE?')
        return actual

    def set_trigger_source(self, external):
        """
        Set the trigger source either to external or immediate.
        If external is true, trigger will be set accordingly
        otherwise immediate triggering will be chosen.
        """
        if external:
            self.instr.write('TRIGGER:SOURCE External')
        else:
            self.instr.write('TRIGGER:SOURCE Immediate')
        return external

    def read_dc_voltage(self):
        """Read a voltage"""
        raw = self.instr.query(':MEASURE:VOLTAGE:DC?')
        voltage = float(raw)
        return voltage

    def read_ac_voltage(self):
        """Read a voltage"""
        raw = self.instr.query(':MEASURE:VOLTAGE:AC?')
        voltage = float(raw)
        return voltage

    def next_reading(self):
        """Read next reading"""
        t0 = time.time()
        while not self.measurement_available():
            time.sleep(0.001)
            if (time.time() - t0) > 10:
                # Todo: This is not good enough
                print('Keithley 2000 TIMEOUT!')
                break
        raw = self.instr.query(':DATA?')
        voltage = float(raw)
        return voltage

    def measurement_available(self):
        # todo: Check if pyvisa has some neat trick for this
        meas_event = int(self.instr.query('STATUS:MEASUREMENT:EVENT?'))
        mav_bit = 5
        mav = (meas_event & 2 ** mav_bit) == 2 ** mav_bit
        return mav


if __name__ == '__main__':
    device = '/dev/serial/by-id/usb-FTDI_Chipi-X_FT6EYK1T-if00-port0'
    DMM = Keithley2000(
        interface='serial',
        device=device,
        baudrate=9600,
    )
    print(repr(DMM.instr.query("*IDN?")))
    print(DMM.set_bandwith())

    # Errors:
    # +802 - RS232 overrun
    # -113 - Undefined header
    DMM.set_trigger_source(external=False)

    DMM.set_range(0)
    for _ in range(0, 10):
        # print()
        # print(DMM.read_software_version())
        # DMM.set_trigger_source(external=False)
        voltage = DMM.next_reading()
        print(voltage)

    # TODO! Something changes with the configuration when this
    # command is called, measurement is much slower and
    # NPLC command fails?!?!
    # print(DMM.configure_measurement_type('volt:ac'))
    # print(DMM.read_dc_voltage())
    # print(DMM.read_dc_voltage())
