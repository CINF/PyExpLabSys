import pyvisa


class TTISMU4001:
    def __init__(self, port='/dev/ttyACM0'):
        rm = pyvisa.ResourceManager()
        self.instr = rm.open_resource(
            'ASRL/dev/ttyACM0::INSTR',
            baud_rate=9600,
            data_bits=8,
            parity=pyvisa.constants.Parity.none,
            stop_bits=pyvisa.constants.StopBits.one,
            write_termination='\r\n',
            read_termination='\r\n',
        )
        # Update self.source_function:
        self.set_source_function()

    def output_state(self, output_state: bool = None, node: int = 0):
        """
        Turn the output on or off
        """
        if output_state is not None:
            if output_state:
                cmd = 'OUTPUT:STATE ON'
            else:
                cmd = 'OUTPUT:STATE OFF'
            self.instr.write(cmd)
        cmd = 'OUTPUT:STATE?'
        actual_state_raw = self.instr.query(cmd)
        actual_state = '1' in actual_state_raw
        return actual_state

    def set_output_level(self, level: float = None):
        """
        Set the output level. If level is None, no changes
        are made, but the actual configured value is returned.
        Notice - this is not a measurement but the configured
        wanted output level.
        """
        if self.source_function == 'i':
            cmd_base = 'SOURCE:CURRENT:FIXED'
        else:
            cmd_base = 'SOURCE:VOLTAGE:FIXED'
        if level is not None:
            cmd = cmd_base + ' {}'.format(level)
            self.instr.write(cmd)

        cmd = cmd_base + '?'
        actual = float(self.instr.query(cmd))
        return actual

    def set_source_function(self, function: str = None, source_range: float = None):
        if function is not None:
            if function.lower() in ('i', 'current'):
                self.instr.write('SYSTEM:FUNCTION:MODE SOURCECURRENT')
            if function.lower() in ('v', 'voltage'):
                self.instr.write('SYSTEM:FUNCTION:MODE SOURCEVOLTAGE')

        # if source_range is not None:
        # For now we use only auto-range. This will be implemented later

        # TODO: PARSE THIS INTO ENUM OF VOLTAGE AND CURRENT
        actual_function_raw = self.instr.query('SYSTEM:FUNCTION:MODE?')
        if 'curr' in actual_function_raw.lower():
            actual_function = 'i'
        else:
            actual_function = 'v'
        self.source_function = actual_function
        return actual_function

    def set_limit(self, level: float = None):
        """
        Set the desired limit for voltage or current depending on current
        source function.
        """
        if self.source_function == 'i':
            cmd_base = 'SOURCE:CURRENT:VOLTAGE:LIMIT'
        else:
            cmd_base = 'SOURCE:VOLTAGE:CURRENT:LIMIT'

        if level is not None:
            cmd = cmd_base + ' {}'.format(level)
            self.instr.write(cmd)

        cmd = cmd_base + '?'
        actual = float(self.instr.query(cmd))
        return actual

    def read_latest(self):
        primary = float(self.instr.query('MEASURE:PRIMARY:LIVEDATA?'))
        secondary = float(self.instr.query('MEASURE:SECONDARY:LIVEDATA?'))
        reading = {
            'source_value': primary,
            'value': secondary,
        }
        # reading['timestamp'] =
        return reading


if __name__ == '__main__':
    smu = TTISMU4001()

    print(smu.instr.query('*IDN?'))
    print(smu.output_state(True))
    # print(smu.set_source_function('i'))
    # print(smu.output_state(True))

    print(smu.read_latest())
    # print(smu.set_limit(2e-3))

    # print(smu.set_output_level(1e-3))
    # print(smu.set_output_level())
