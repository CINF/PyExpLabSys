""" Simple driver for Keithley 2400 SMU """
from PyExpLabSys.drivers.scpi import SCPI


class Keithley2400(SCPI):
    """Simple driver for Keithley 2400 SMU"""

    def __init__(
        self,
        interface,
        hostname='',
        device='',
        baudrate=9600,
        gpib_address=None,
        line_ending='\n',
    ):
        if interface == 'serial':
            SCPI.__init__(
                interface=interface,
                device=device,
                baudrate=baudrate,
                line_ending='\n',
            )
            self.comm_dev.timeout = 2
            self.comm_dev.rtscts = False
            self.comm_dev.xonxoff = False
        if interface == 'lan':
            SCPI.__init__(self, interface=interface, hostname=hostname)
        if interface == 'gpib':
            SCPI.__init__(self, interface=interface, gpib_address=gpib_address)

    def output_state(self, output_state: bool = None):
        """Turn the output on or off"""
        if output_state is not None:
            if output_state:
                self.scpi_comm('OUTPUT:STATE 1')
            else:
                self.scpi_comm('OUTPUT:STATE 0')
        actual_state_raw = self.scpi_comm('OUTPUT:STATE?')
        actual_state = actual_state_raw[0] == '1'
        return actual_state

    def set_current_measure_range(self, current_range=None):
        """Set the current measurement range"""
        # TODO!
        raise NotImplementedError

    def set_integration_time(self, nplc: float = None):
        """
        Set the measurement integration time
        In principle the current ant voltage value can be set
        independently, but for now they are synchronized
        """
        if nplc is not None:
            if nplc < 0.01:
                nplc = 0.01
            if nplc > 10:
                nplc = 10
            self.scpi_comm('SENSE:CURRENT:NPLCYCLES {}'.format(nplc))
            self.scpi_comm('SENSE:VOLTAGE:NPLCYCLES {}'.format(nplc))
        current_nplc = float(self.scpi_comm('SENSE:CURRENT:NPLCYCLES?'))
        return current_nplc

    def _parse_status(self, status_string):
        status_table = {
            0: ('OFLO', 'Measurement was made while in over-range'),
            1: ('Filter', 'Measurement was made with the filter enabled'),
            # 2: ('Front/Rear', 'FRONT terminals are selected'),
            3: ('Compliance', 'In real compliance'),
            4: ('OVP', 'Over voltage protection limit was reached'),
            5: ('Math', 'Math expression (calc1) is enabled'),
            6: ('Null', 'Null is enabled'),
            7: ('Limits', 'Limit test (calc2) is enabled'),
            # Bits 8 and 9 (Limit Results) — Provides limit test results
            # (see scpi command reference 18-51)
            10: ('Auto-ohms', 'Auto-ohms enabled'),
            11: ('V-Meas', 'V-Measure is enabled'),
            12: ('I-Meas', 'I-Measure is enabled'),
            13: ('Ω-Meas', 'Ω-Measure is enabled'),
            14: ('V-Sour', 'V-Source used'),
            15: ('I-Sour', 'I-Source used'),
            16: ('Range Compliance', 'In range compliance'),
            17: ('Offset Compensation', 'Offset Compensated Ohms is enabled'),
            18: ('Contact check failure', '(see Appendix F in manual'),
            # Bits 19, 20 and 21 (Limit Results) — Provides limit test results
            # (see scpi command reference 18-51)
            22: ('Remote Sense', '4-wire remote sense selected'),
            23: ('Pulse Mode', 'In the Pulse Mode'),
        }

        status_messages = []
        status_value = int(float(status_string))
        # Strip 0b from the string and fill to 24 bits
        bin_status = bin(status_value)[2:].zfill(24)
        bin_status = bin_status[::-1]  # Reverse string, to get correct byte order
        for i in range(0, 24):
            bit_value = int(bin_status[i]) == 1
            if bit_value and i in status_table:
                status_messages.append(status_table[i])
        return status_messages

    def read_current(self):
        """
        Read the measured current
        Returns None if the output is off.
        """
        if self.output_state():
            raw = self.scpi_comm('MEASURE:CURRENT?')
        else:
            raw = None
        if raw is None:
            return

        # Values are: voltage, current, ohm, time, status
        # Only the current is measured, voltage is either
        # NaN or the source-setpoint.
        values = raw.split(',')
        current = float(values[1])
        # timestamp = float(values[3])
        # print(self._parse_status(values[4]))
        # Also return timestamp?
        return current

    def read_voltage(self):
        """Read the measured voltage"""
        if self.output_state():
            raw = self.scpi_comm('MEASURE:VOLTAGE?')
        else:
            raw = None
        if raw is None:
            return

        # Values is: voltage, current, ohm, time, status
        # Only the voltage is measured, current is either
        # NaN or the source-setpoint.
        values = raw.split(',')
        voltage = float(values[0])
        # timestamp = float(values[3])
        # print(self._parse_status(values[4]))
        # Also return timestamp?
        return voltage

    def set_source_function(self, function=None, source_range=None):
        if function.lower() in ('i', 'I'):
            self.scpi_comm(':SOURCE:FUNCTION CURRENT')
            self.scpi_comm(':SOURCE:CURRENT:RANGE {}'.format(source_range))
        if function.lower() in ('v', 'V'):
            self.scpi_comm(':SOURCE:FUNCTION VOLTAGE')
            self.scpi_comm(':SOURCE:VOLTAGE:RANGE {}'.format(source_range))

        actual_function = self.scpi_comm('SOURCE:FUNCTION?')
        return actual_function

    def set_sense_function(self, function, sense_range=None):
        """
        Set the sense range, a value of None returns the current value without
        changing the actual value. A range value of 0 indicates auto-range.
        """
        if function.lower() in ('i' 'current'):
            self.scpi_comm(':SENSE:FUNCTION:ON "CURRENT"')
            if sense_range == 0:
                self.scpi_comm(':SENSE:CURRENT:RANGE:AUTO ON')
            else:
                if sense_range is not None:
                    self.scpi_comm(':SENSE:CURRENT:RANGE {}'.format(sense_range))
        if function.lower() in ('v', 'voltage'):
            #  TODO: Configure read-back!!!
            self.scpi_comm(':SENSE:FUNCTION:ON "VOLTAGE"')
            if sense_range == 0:
                self.scpi_comm(':SENSE:VOLTAGE:RANGE:AUTO ON')
            else:
                if sense_range is not None:
                    self.scpi_comm(':SENSE:VOLTAGE:RANGE {}'.format(sense_range))
        self.scpi_comm(':SENSE:FUNCTION:ON?')
        self.clear_buffer()
        raw = self.scpi_comm(':SENSE:FUNCTION:ON?')
        return raw

    def set_current_limit(self, current: float = None):
        """Set the desired current limit"""
        if current is not None:
            self.scpi_comm('CURRENT:PROTECTION {:.9f}'.format(current))
        actual = self.scpi_comm('CURRENT:PROTECTION?')
        return actual

    def set_voltage_limit(self, voltage: float = None):
        """Set the desired voltate limit"""
        if voltage is not None:
            print(':VOLTAGE:PROTECTION {:.9f}'.format(voltage))
            self.scpi_comm(':VOLTAGE:PROTECTION {:.9f}'.format(voltage))
        actual = self.scpi_comm(':VOLTAGE:PROTECTION?')
        return actual

    def set_current(self, current: float):
        """Set the desired current"""
        self.scpi_comm('SOURCE:CURRENT {:.9f}'.format(current))
        return True

    def set_voltage(self, voltage: float):
        """Set the desired current"""
        self.scpi_comm('SOURCE:VOLT {:.9f}'.format(voltage))
        return True


if __name__ == '__main__':
    import time

    GPIB = 22
    SMU = Keithley2400(interface='gpib', gpib_address=GPIB)

    SMU.set_source_function('v')
    SMU.output_state(True)

    # print(SMU.scpi_comm(':TRIGGER:OUTPUT SENSE'))
    print(SMU.scpi_comm(':TRIGGER:OUTPUT SOURCE'))
    print(SMU.scpi_comm(':TRIGGER:OUTPUT?'))

    print(SMU.scpi_comm(':TRIGGER:OLINE?'))
    print(SMU.scpi_comm(':TRIGGER:OLINE 2'))

    for i in range(0, 10):
        SMU.set_voltage(i / 10.0)
        time.sleep(0.5)
        print(SMU.scpi_comm(':TRIGGER:OUTPUT SENSE'))
        current = SMU.read_current()
        print(SMU.scpi_comm(':TRIGGER:OUTPUT NONE'))
        voltage = SMU.read_voltage()
        print(
            'Current: {:.1f}uA. Voltage: {:.2f}mV. Resistance: {:.1f}ohm'.format(
                current * 1e6, voltage * 1000, voltage / current
            )
        )
