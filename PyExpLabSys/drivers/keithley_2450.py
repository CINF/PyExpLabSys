import time
import datetime
import pyvisa as visa


class Keithley2450:
    def __init__(self, interface='lan', hostname=''):
        if interface == 'lan':
            visa_string = 'TCPIP0::{}::inst0::INSTR'.format(hostname)
        rm = visa.ResourceManager()
        self.instr = rm.open_resource(visa_string)

        cmd = 'smu.measure.displaydigits = smu.DIGITS_6_5'
        self.instr.write(cmd)

    def reset_instrument(self):
        """
        Send the reset comand to the instrument.
        """
        self.instr.write('reset()')
        time.sleep(0.5)

    def use_rear_terminals(self, use_rear: bool = True):
        """
        If True (default), the instrument will use the recommended configuration
        of using the rear triax terminals. If False the front banana's are used.
        """
        if use_rear:
            self.instr.write('smu.measure.terminals = smu.TERMINALS_REAR')
        else:
            self.instr.write('smu.measure.terminals = smu.TERMINALS_FRONT')
        return use_rear

    def output_state(self, output_state: bool = None):
        """
        Turn the output on or off
        """
        if output_state is not None:
            if output_state:
                self.instr.write('smu.source.output = smu.ON')
            else:
                self.instr.write('smu.source.output = smu.OFF')
        actual_state_raw = self.instr.query('print(smu.source.output)')
        actual_state = actual_state_raw.find('smu.ON') > -1
        return actual_state

    def set_current(self, current: float):
        """DEPRECATED: Here only for compatibility - will be removed"""
        print('k2450 - set-current is deprecated!')
        self.set_output_level(current)
        return True

    def set_voltage(self, voltage: float):
        """DEPRECATED: Here only for compatibility - will be removed"""
        print('k2450 - set-voltage is deprecated!')
        self.set_output_level(voltage)
        return True

    def set_output_level(self, level: float = None):
        """
        Set the output level. If level is None, no changes
        are made, but the actual configured value is returned.
        Notice - this is not a measurement but the configured
        wanted output level.
        """
        if level is not None:
            cmd = 'smu.source.level={}'.format(level)
            self.instr.write(cmd)
        actual = float(self.instr.query('print(smu.source.level)'))
        return actual

    def set_source_function(self, function: str = None, source_range: float = None):
        if function.lower() in ('i', 'current'):
            self.instr.write('smu.source.func = smu.FUNC_DC_CURRENT')
        if function.lower() in ('v', 'voltage'):
            self.instr.write('smu.source.func = smu.FUNC_DC_VOLTAGE')

        if source_range is not None:
            if source_range == 0:
                self.instr.write('smu.source.autorange = smu.ON')
        else:
            self.instr.write('smu.source.autorange = smu.OFF')
            self.instr.write('smu.source.range = {}'.format(source_range))

        # TODO - Readback currently hard-coded!
        self.instr.write('smu.source.readback = smu.ON')

        actual_function = self.instr.query('print(smu.source.func)')
        # TODO: PARSE THIS INTO ENUM OF VOLTAGE AND CURRENT
        return actual_function

    def remote_sense(self, action: bool = None):
        if action is not None:
            if action:
                self.instr.write('smu.measure.sense = smu.SENSE_4WIRE')
            else:
                self.instr.write('smu.measure.sense = smu.SENSE_2WIRE')
        actual_state = self.instr.query('print(smu.measure.sense)').find('4WIRE') > -1
        return actual_state

    def set_sense_function(self, function: str = None, sense_range: float = None):
        """
        Set the sense range, a value of None returns the current value without
        changing the actual value. A range value of 0 indicates auto-range.
        """
        # TODO:
        # Many other measurement functions exists, such as resistance, power
        # and math functions
        if function.lower() in ('i', 'current'):
            self.instr.write('smu.measure.func = smu.FUNC_DC_CURRENT')
        if function.lower() in ('v', 'voltage'):
            self.instr.write('smu.measure.func = smu.FUNC_DC_VOLTAGE')

        if sense_range == 0:
            self.instr.write('smu.measure.autorange = smu.ON')
        else:
            cmd = 'smu.measure.range = {}'.format(sense_range)
            self.instr.write(cmd)

        actual_function = self.instr.query('print(smu.measure.func)')
        # TODO: PARSE THIS INTO ENUM OF VOLTAGE AND CURRENT
        return actual_function

    def set_auto_zero(self, function: str, action: bool = None):
        """
        Set auto-zero behaviour.
        Action can be 'on', 'off', or None
        """
        if action is not None:
            if action:
                self.instr.write('smu.measure.autozero.enable = smu.ON')
            else:
                self.instr.write('smu.measure.autozero.enable = smu.OFF')

        actual_state = (
            self.instr.query('print(smu.measure.autozero.enable)').find('ON') > -1
        )
        return actual_state

    def auto_zero_now(self):
        """
        Perform a single auto-zero
        """
        self.instr.write('smu.measure.autozero.once()')
        return True

    def set_limit(self, value: float):
        """
        Set the desired limit for voltage or current depending on current
        source function.
        TODO: Query the measure range to check if value is legal
        """
        cmd = 'print(smu.source.func)'
        source_func = self.instr.query(cmd)
        if source_func.find('VOLTAGE') > -1:
            cmd = 'smu.source.ilimit.level'
        else:
            cmd = 'smu.source.vlimit.level'
        if value is not None:
            limit_cmd = cmd + '={}'.format(value)
            self.instr.write(limit_cmd)
        return value

    # Compatibility function, could be removed
    def set_current_limit(self, current: float = None):
        cmd = 'smu.source.func = smu.FUNC_DC_VOLTAGE'
        self.instr.write(cmd)
        if current is not None:
            self.set_limit(value=current)
        return current

    def query_limit(self):
        """
        Query the current source limit
        """
        query_cmd = 'print(smu.source.ilimit.level)'
        print(query_cmd)
        limit = float(self.instr.query(query_cmd))
        return limit

    def buffer_exists(self, buffer: str):
        cmd = 'print({} == nil)'.format(buffer)
        buffer_exists = self.instr.query(cmd).strip() == 'false'
        return buffer_exists

    def make_buffer(self, buffer: str, size: int = 10):
        """
        Make a buffer of type FULL and fillmode continous
        @return: True if created, false if buffer was already present
        """
        if size < 10:
            return False

        if self.buffer_exists(buffer):
            return False

        # TODO: Check if STYLE_FULL actually makes sense
        cmd = '{} = buffer.make({}, buffer.STYLE_FULL)'.format(buffer, size)
        self.instr.write(cmd)

        cmd = '{}.fillmode = buffer.FILL_CONTINUOUS'.format(buffer)
        self.instr.write(cmd)
        return True

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
            self.instr.write('smu.measure.nplc = {}'.format(nplc))

        print(self.instr.query('print(smu.measure.nplc)'))
        current_nplc = float(self.instr.query('print(smu.measure.nplc)'))
        return current_nplc

    def trigger_measurement(self, buffer: str = 'defbuffer1'):
        cmd = 'print(smu.measure.read({}))'.format(buffer)
        value = float(self.instr.query(cmd))
        return value

    def clear_buffer(self, buffer: str = 'defbuffer1'):
        if not self.buffer_exists(buffer):
            return False
        self.instr.write('{}.clear()'.format(buffer))
        return True

    # def elements_in_buffer(self, buffer: str = 'defbuffer1'):

    def read_latest(self, buffer: str = 'defbuffer1'):
        reading = {}
        cmd = 'a={}; n = a.endindex'.format(buffer)
        self.instr.write(cmd)

        # Todo: bufferVar.statuses (manual 8-34)
        # Todo: bufferVar.sourcestatuses (manual 8-29)
        cmd = 'printbuffer(n, n, a, a.sourcevalues, a.timestamps)'
        raw = self.instr.query(cmd).strip().split(',')
        reading['value'] = float(raw[0])
        reading['source_value'] = float(raw[1])
        reading['timestamp'] = datetime.datetime.strptime(
            raw[2].strip()[0:25], '%m/%d/%Y %H:%M:%S.%f'
        )
        return reading


if __name__ == '__main__':
    hostname = '192.168.0.3'
    k = Keithley2450(interface='lan', hostname=hostname)

    k.instr.write('smu.source.autorange = smu.ON')
    # self.instr.write('smu.source.range = {}'.format(source_range))

    exit()

    limit = 1e-6
    k.set_sense_function('i', sense_range=limit)

    print(k.buffer_exists('gate_data'))

    k.make_buffer('gate_data', 10)
    for i in range(0, 100):

        k.trigger_measurement(buffer='gate_data')
        reading = k.read_latest(buffer='gate_data')
        print(reading)
