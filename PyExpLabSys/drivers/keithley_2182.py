""" Simple driver for Keithley 2182 Nanovolt Meter """
import time

import pyvisa


class Keithley2182:
    """
    Simple driver for Keithley 2182 Nanovolt Meter
    Actual implementation performed on a 2182a - please
    double check if you have a 2182.
    """

    def __init__(self, interface, hostname='', device='', baudrate=19200):
        rm = pyvisa.ResourceManager('@py')
        if interface == 'serial':
            conn_string = 'ASRL{}::INSTR'.format(device)
            self.instr = rm.open_resource(conn_string)
            self.instr.read_termination = '\r'
            self.instr.write_termination = '\r'
            self.instr.baud_rate = baudrate
        # For now, turn off continous trigger - this might need reconsideration
        # self.scpi_comm('INIT:CONT OFF')

    def set_range(self, channel1: float = None, channel2: float = None):
        """
        Set the measurement range of the device, 0 will indicate auto-range
        """
        print('Set range of channel 1')
        if channel1 is not None:
            if channel1 > 120:
                channel1 = 120
            if channel1 == 0:
                self.instr.write(':SENSE:VOLT:CHANNEL1:RANGE:AUTO ON')
            else:
                self.instr.write(':SENSE:VOLT:CHANNEL1:RANGE {:.2f}'.format(channel1))

        if channel2 is not None:
            if channel2 > 12:
                channel2 = 12
            if channel2 == 0:
                self.instr.write(':SENSE:VOLTAGE:CHANNEL2:RANGE:AUTO ON')
            else:
                self.instr.write(':SENSE:VOLT:CHANNEL2:RANGE {:.2f}'.format(channel2))
        print('Check the actual range')
        actual_channel1_raw = self.instr.query(':SENSE:VOLTAGE:CHANNEL1:RANGE?')
        actual_channel2_raw = self.instr.query(':SENSE:VOLTAGE:CHANNEL2:RANGE?')
        range1 = float(actual_channel1_raw)
        range2 = float(actual_channel2_raw)
        print('Value is: ', range1)
        return range1, range2

    def set_integration_time(self, nplc: float = None):
        """
        Set the measurement integration time
        """
        if nplc is not None:
            if nplc < 0.01:
                nplc = 0.01
            if nplc > 60:
                nplc = 60
            self.instr.write('SENSE:VOLTAGE:NPLCYCLES {}'.format(nplc))
            # print('waiting....')
            time.sleep(nplc * 0.25)
            # print('done')
        current_nplc = float(self.instr.query('SENSE:VOLTAGE:NPLCYCLES?'))
        return current_nplc

    def set_trigger_source(self, external):
        """
        Set the trigger source either to external or immediate.
        If external is true, trigger will be set accordingly
        otherwise immediate triggering will be chosen.
        """
        if external:
            self.instr.write(':TRIGGER:SOURCE External')
        else:
            self.instr.write(':TRIGGER:SOURCE Immediate')
        return external

    def read_fresh(self):
        """
        Read a single value from current channel. This will also be a new value
        (or will fail if channel is not trigged.
        """
        raw = self.instr.query(':DATA:FRESh?')  # DF? also works
        try:
            voltage = float(raw)
        except ValueError:
            voltage = None
        return voltage

    def read_voltage(self, channel: int):
        """Read the measured voltage"""
        if channel not in (1, 2):
            return None
        self.instr.write(":SENSE:FUNC 'VOLT:DC'")
        time.sleep(0.5)
        self.instr.write(':SENSE:CHANNEL {}'.format(channel))
        time.sleep(0.5)
        # raw = self.instr.query(':READ?')
        raw = self.read_fresh()
        voltage = float(raw)
        return voltage


if __name__ == '__main__':
    # usb-1a86_USB2.0-Ser_-if00-port0 # Vxx
    # usb-FTDI_Chipi-X_FT6EYK1T-if00-port0 #  DMM
    # usb-FTDI_Chipi-X_FT6F1A7R-if00-port0 # Old gate
    # usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0  # Vxy
    # NVM = Keithley2182(interface='gpib', gpib_address=GPIB)
    NVM = Keithley2182(
        interface='serial',
        device='/dev/serial/by-id/usb-1a86_USB2.0-Ser_-if00-port0',
    )

    print(NVM.instr.query('*IDN?'))
    print(NVM.set_range(1, 0.1))
