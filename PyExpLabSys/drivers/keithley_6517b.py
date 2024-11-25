"""
Simple driver for Keithley 6517B electrometer
"""

import pyvisa

# Notice: The code is NOT abstract towards this list... changing it will
# result in values being intermixed
STANDARD_READ_PARAMS = [
    'READING',
    'SOURCE',
    'RELATIVE',
    'SOURSTATUS',
    'STATUS',
    'SOURUNIT',
    'UNIT',
]


class Keithley6517B():
    """Simple driver for Keithley 6517B electrometer"""

    def __init__(self, device, baudrate=19200):
        rm = pyvisa.ResourceManager('@py')
        conn_string = 'ASRL{}::INSTR'.format(device)
        self.instr = rm.open_resource(conn_string)
        self.instr.set_visa_attribute(
            pyvisa.constants.VI_ATTR_ASRL_FLOW_CNTRL,
            pyvisa.constants.VI_ASRL_FLOW_XON_XOFF,
        )
        self.instr.read_termination = '\r'
        self.instr.write_termination = '\r'
        self.instr.baud_rate = baudrate

    def output_state(self, output_state: bool = None):
        """Turn the output on or off"""
        if output_state is not None:
            if output_state:
                self.instr.write('OUTPUT1 ON')
            else:
                self.instr.write('OUTPUT1 OFF')

        actual_state_raw = self.instr.query('OUTPUT1?')
        actual_state = int(actual_state_raw[0]) == 1
        return actual_state

    def set_voltage(self, voltage=None):
        """ Set the desired voltage """
        if voltage is not None:
            cmd = ':SOURce:VOLTage:LEVel:IMMediate:AMPLitude {:.9f}'.format(voltage)
            self.instr.write(cmd)

        cmd = ':SOURce:VOLTage:LEVel:IMMediate:AMPLitude?'
        value_raw = self.instr.query(cmd)
        value = float(value_raw)
        return value

    def _parse_reading(self, raw_reading):
        exp_pos = raw_reading.find('E+')
        unit_end = raw_reading.find(',')
        time_end = raw_reading.find(',', unit_end + 1)
        reading_end = raw_reading.find('RDNG#')
        # Status:
        # N: Normal,    Z: Zero check enabled,  O: Overflow,  # U: Underflow
        # R: Reference (relative offset),       L: Out of limit
        reading = {
            'value': float(raw_reading[0:exp_pos + 4]),
            'status': raw_reading[exp_pos + 4:exp_pos + 5],
            'unit': raw_reading[exp_pos + 5:unit_end],
            'reading_nr': int(raw_reading[time_end + 2:reading_end]),
        }
        return reading
    
    def read_voltage(self):
        """Read the measured voltage"""
        value_raw = self.instr.query('MEASURE:VOLTAGE?')
        value = self._parse_reading(value_raw)['value']
        return value

    def read_current(self):
        """Read the measured current"""
        value_raw = self.instr.query('MEASURE:CURRENT?')
        value = self._parse_reading(value_raw)['value']
        return raw

    def read_again(self):
        value_raw = self.instr.query(':SENSe:DATA:FRESh?')
        value = self._parse_reading(value_raw)['value']
        return value
    
if __name__ == '__main__':
    import time

    EM = Keithley6517B(device='/dev/ttyUSB1')

    print(EM.instr.query('*IDN?'))

    print('Output state: ', EM.output_state(True))
    print('Output voltage: ', EM.set_voltage(0.0))

    print()

    print(EM.read_voltage())
    exit()
    print(EM.read_again())

    print(EM.read_current())
    print(EM.read_again())

    # for _ in range(0, 10):
    #     EM.instr.write('*TRG')
    #     time.sleep(0.2)
    #     print(EM.instr.query('FETCH?'))
