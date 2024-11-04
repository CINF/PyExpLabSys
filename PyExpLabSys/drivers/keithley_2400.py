""" Simple driver for Keithley 2400 SMU """
import pyvisa


class Keithley2400:
    """Simple driver for Keithley 2400 SMU"""

    def __init__(self, interface, device='', baudrate=9600, gpib_address=None):
        rm = pyvisa.ResourceManager('@py')
        if interface == 'serial':
            conn_string = 'ASRL{}::INSTR'.format(device)
            self.instr = rm.open_resource(conn_string)
            # self.instr.set_visa_attribute(
            #     pyvisa.constants.VI_ATTR_ASRL_FLOW_CNTRL,
            #     pyvisa.constants.VI_ASRL_FLOW_XON_XOFF,
            # )
            self.instr.read_termination = '\n'
            self.instr.write_termination = '\n'
            self.instr.baud_rate = baudrate
        if interface == 'lan':
            # The 2400 actually no not have a LAN interface, but 2450 do
            conn_string = 'TCPIP::{}::inst0::INSTR'.format(device)
            self.instr = rm.open_resource(conn_string)
        if interface == 'gpib':
            pass

    def output_state(self, output_state: bool = None):
        """Turn the output on or off"""
        if output_state is not None:
            if output_state:
                self.instr.write('OUTPUT:STATE 1')
            else:
                self.instr.write('OUTPUT:STATE 0')
        actual_state_raw = self.instr.query('OUTPUT:STATE?')
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
            self.instr.write('SENSE:CURRENT:NPLCYCLES {}'.format(nplc))
            self.instr.write('SENSE:VOLTAGE:NPLCYCLES {}'.format(nplc))
        current_nplc = float(self.instr.query('SENSE:CURRENT:NPLCYCLES?'))
        return current_nplc

    @staticmethod
    def _parse_status(status_string):
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
            raw = self.instr.query('MEASURE:CURRENT?')
        else:
            raw = None
        if raw is None:
            return

        if ',' in raw:
            # Values are: voltage, current, ohm, time, status
            # Only the current is measured, voltage is either
            # NaN or the source-setpoint.
            values = raw.split(',')
            current = float(values[1])
        else:
            current = float(raw)
        # timestamp = float(values[3])
        # print(self._parse_status(values[4]))
        # Also return timestamp?
        return current

    def read_voltage(self):
        """Read the measured voltage"""
        if self.output_state():
            raw = self.instr.query('MEASURE:VOLTAGE?')
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
        if function in ('i', 'I'):
            self.instr.write('SOURCE:FUNCTION CURRENT')
            if source_range:
                self.instr.write(':SOURCE:CURRENT:RANGE {}'.format(source_range))
        if function in ('v', 'V'):
            self.instr.write('SOURCE:FUNCTION VOLTAGE')
            if source_range:
                self.instr.write(':SOURCE:VOLTAGE:RANGE {}'.format(source_range))

        actual_function = self.instr.query('SOURCE:FUNCTION?')
        return actual_function

    def set_sense_function(self, function, sense_range=None):
        """
        Set the sense range, a value of None returns the current value without
        changing the actual value. A range value of 0 indicates auto-range.
        """
        if function.lower() in ('i' 'current'):
            self.instr.write(':SENSE:FUNCTION:ON "CURRENT"')
            if sense_range == 0:
                self.instr.write(':SENSE:CURRENT:RANGE:AUTO ON')
            else:
                self.instr.write(':SENSE:CURRENT:RANGE {}'.format(sense_range))
        if function.lower() in ('v', 'voltage'):
            #  TODO: Configure read-back!!!
            self.instr.write(':SENSE:FUNCTION:ON "VOLTAGE"')
            if sense_range == 0:
                self.instr.write(':SENSE:VOLTAGE:RANGE:AUTO ON')
            else:
                self.instr.write(':SENSE:VOLTAGE:RANGE {}'.format(sense_range))

        # Double read was needed with the old scpi module, hopefully no wwith pyvisa
        # self.scpi_comm(':SENSE:FUNCTION:ON?')
        # self.clear_buffer()
        raw = self.instr.query(':SENSE:FUNCTION:ON?')
        return raw

    def set_current_limit(self, current: float = None):
        """Set the desired current limit"""
        if current is not None:
            self.instr.write('CURRENT:PROTECTION {:.9f}'.format(current))
            print('K2400: LIMIT IS NOW: ', current)
        raw = self.instr.query('CURRENT:PROTECTION?')
        actual = float(raw)
        return actual

    def set_voltage_limit(self, voltage: float = None):
        """Set the desired voltate limit"""
        if voltage is not None:
            self.instr.write('VOLTAGE:PROTECTION {:.9f}'.format(voltage))
        raw = self.instr.query('VOLTAGE:PROTECTION?')
        actual = float(raw)
        return actual

    def set_current(self, current: float):
        """Set the desired current"""
        self.instr.write('SOURCE:CURRENT {:.9f}'.format(current))
        return True

    def set_voltage_range(self, voltage: float):
        self.instr.write(':SOURCE:VOLTAGE:RANGE {:.9f}'.format(voltage))

    def set_voltage(self, voltage: float):
        """Set the desired current"""
        self.instr.write('SOURCE:VOLT {:.9f}'.format(voltage))
        return True

    def read_volt_and_current(self):
        # TODO - CONFIGURE TO ENSURE RIGHT SYNTAX OF RETURN!
        # Also try to configure to measure actual voltage
        # self.scpi_comm(':INIT')
        raw = self.instr.query(':READ?')
        fields = raw.split(',')
        voltage = float(fields[0])
        current = float(fields[1])
        return voltage, current


if __name__ == '__main__':
    import time

    device = '/dev/serial/by-id/usb-FTDI_Chipi-X_FT6F1A7R-if00-port0'
    SMU = Keithley2400(
        interface='serial',
        device=device,
        baudrate=19200,
    )
    print(SMU.instr.query('*IDN?'))
    exit()

    # GPIB = 22
    # SMU = Keithley2400(interface='gpib', gpib_address=GPIB)

    SMU.set_source_function('v')
    SMU.output_state(True)
    # SMU.set_voltage_range(voltage=90)
    SMU.set_voltage(0.12)

    print(SMU.read_current())
    SMU.set_current_limit(1e-7)

    time.sleep(1)

    cmd = 'READ?'
    for i in range(0, 50):
        print(SMU.read_volt_and_current())

    # print(SMU.read_current())

    exit()

    # # print(SMU.scpi_comm(':TRIGGER:OUTPUT SENSE'))
    print(SMU.scpi_comm(':TRIGGER:OUTPUT SOURCE'))
    print(SMU.scpi_comm(':TRIGGER:OUTPUT?'))

    print(SMU.scpi_comm(':TRIGGER:OLINE?'))
    print(SMU.scpi_comm(':TRIGGER:OLINE 2'))

    # for i in range(0, 10):
    #     SMU.set_voltage(i / 10.0)
    #     time.sleep(0.5)
    #     print(SMU.scpi_comm(':TRIGGER:OUTPUT SENSE'))
    #     current = SMU.read_current()
    #     print(SMU.scpi_comm(':TRIGGER:OUTPUT NONE'))
    #     voltage = SMU.read_voltage()
    #     print(
    #         'Current: {:.1f}uA. Voltage: {:.2f}mV. Resistance: {:.1f}ohm'.format(
    #             current * 1e6, voltage * 1000, voltage / current
    #         )
    #     )
