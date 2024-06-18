"""
Simple driver for Keithley 2450 SMU
"""
from PyExpLabSys.drivers.keithley_2400 import Keithley2400

# Notice, SOURCE will report either setpoint or readback
# depending on configuration
# TODO: Allow setting of the READBACK parameter

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


class Keithley2450(Keithley2400):
    """Simple driver for Keithley 2450 SMU"""

    def __init__(
        self, interface, hostname='', device='', baudrate=9600, gpib_address=None
    ):
        super().__init__(
            interface=interface,
            device=device,
        )
        self.srp = ', '.join(STANDARD_READ_PARAMS)
        self.latest_fetch_time = 0  # Keeps latest result from FETCh?

        # print(self.clear_comm_buffer())
        # error = self.scpi_comm("*ESR?")
        # self.scpi_comm("*cls")

    @staticmethod
    def _parse_raw_reading(reading):
        reading_list = reading.split(',')
        if len(reading_list) < len(STANDARD_READ_PARAMS):
            # Reading is malformed
            return None

        value = float(reading_list[0])
        source_value = float(reading_list[1])
        delta_time = float(reading_list[2])

        source_status = reading_list[3]  # This field seems to be undocumented?
        status = reading_list[4]  # TODO: Parse this!

        source_unit = reading_list[5]
        value_unit = reading_list[6]

        reading = {
            'value': value,
            'source_value': source_value,
            'delta_time': delta_time,
            'source_status': source_status,
            'status': status,
            'source_unit': source_unit,
            'value_unit': value_unit,
        }
        return reading

    # *********************************** #
    # Refactor these two

    # Notice: This function is actually different between 2400 and 2450
    # many of the other changes can be backported to the 2400 driver
    def set_voltage_limit(self, voltage: float = None):
        """Set the desired voltage limit"""
        if voltage is not None:
            self.instr.write(':SOURCE:CURRENT:VLIMIT {:.9f}'.format(voltage))
        actual = self.instr.query(':SOURCE:CURRENT:VLIMIT?')
        return actual

    # Notice: This function is actually different between 2400 and 2450
    # many of the other changes can be backported to the 2400 driver
    def set_current_limit(self, current: float = None):
        """Set the desired voltage limit"""
        if current is not None:
            self.instr.write(':SOURCE:VOLTAGE:ILIMIT {:.9f}'.format(current))
        actual = self.instr.query(':SOURCE:VOLTAGE:ILIMIT?')
        return actual

    # *********************************** #

    def set_auto_zero(self, function: str, action: bool = None):
        """
        Set auto-zero behaviour for a given function (voltage or current).
        Action can be 'on', 'off', or None
        """
        if function.lower() == 'i':
            scpi_function = 'CURRENT'
        elif function.lower() == 'v':
            scpi_function = 'VOLTAGE'
        else:
            raise Exception('Function not allowed: {}'.format(function))

        if action is not None:
            if action:
                scpi_action = 'On'
            else:
                scpi_action = 'Off'

            if scpi_action is not None:
                cmd = ':SENSE:{}:AZERO {}'.format(scpi_function, scpi_action)
                self.instr.write(cmd)

        cmd = ':SENSE:{}:AZERO?'.format(scpi_function)
        reply = self.instr.query(cmd)
        return reply

    def auto_zero_now(self):
        """
        Perform a single auto-zero
        """
        cmd = ':SENSE:AZERO:ONCE'
        self.instr.write(cmd)
        return True

    def remote_sense(self, action: bool = None):
        if action is not None:
            if action:
                scpi_action = 'On'
            else:
                scpi_action = 'Off'
            cmd = 'SENSE:{}:RSENSE {}'
            self.instr.write(cmd.format('VOLTAGE', scpi_action))
            self.instr.write(cmd.format('CURRENT', scpi_action))
            self.instr.write(cmd.format('RESISTANCE', scpi_action))
        cmd = 'SENSE:VOLTAGE:RSENSE?'
        reply = self.instr.query(cmd)
        return reply

    def trigger_measurement(self, buffer='defbuffer1'):
        cmd = ':TRACE:TRIGGER "{}"'.format(buffer)
        self.instr.write(cmd)
        return True

    def make_buffer(self, buffer_name, size=10):
        """
        Make a buffer of type FULL and fillmode continous
        """
        if size < 10:
            return False
        cmd = ':TRACE:MAKE "{}", {}, FULL'.format(buffer_name, size)
        self.instr.write(cmd)

        cmd = ':TRACE:FILL:MODE CONTINUOUS, "{}"'.format(buffer_name)
        self.instr.write(cmd)
        actual_readings = self.elements_in_buffer(buffer_name)
        return True

    def elements_in_buffer(self, buffer='defbuffer1'):
        raw = self.instr.query(':TRACE:ACTUAL? "{}"'.format(buffer))
        actual_readings = int(raw)
        return actual_readings

    def clear_buffer(self, buffer='defbuffer1'):
        self.instr.query(':TRACE:CLEAR "{}"'.format(buffer))
        actual_readings = self.elements_in_buffer(buffer)
        return actual_readings

    def read_from_buffer(self, start, stop, buffer='defbuffer1'):
        data = []
        for i in range(start, stop + 1):
            # cmd = 'TRACE:DATA? {}, {}, "{}", {}'.format(start, stop, buffer, self.srp)
            cmd = 'TRACE:DATA? {}, {}, "{}", {}'.format(i, i, buffer, self.srp)
            raw = self.instr.query(cmd)
            reading = self._parse_raw_reading(raw)
            data.append(reading)
        return data

    def read_latest(self, buffer='defbuffer1'):
        cmd = ':FETCH? "{}", {}'.format(buffer, self.srp)

        dt = 0
        iteration = 0
        while dt <= self.latest_fetch_time:
            if iteration > 10:
                print('Seems we have missed a trigger...')
                self.trigger_measurement(buffer)
                iteration = 0
            iteration += 1
            try:
                # t = time.time()
                raw = self.instr.query(cmd)
                # print('raw read', time.time() - t)
                reading = self._parse_raw_reading(raw)
                if reading is None:
                    continue
                dt = reading['delta_time']
            except ValueError:
                pass
        self.latest_fetch_time = dt
        return reading


if __name__ == '__main__':
    import time

    SMU = Keithley2450(interface='lan', device='192.168.0.30')
    # SMU.make_buffer('gate_data')

    # SMU = Keithley2450(interface='lan', hostname='192.168.0.4')
    # SMU.make_buffer('iv_data')

    # SMU.instr.write('*TRG')

    # for i in range(1, 7):
    #     cmd = ':DIGital:LINE{}:MODE DIGital, OUT'.format(i)
    #    print(cmd)
    #    SMU.instr.write(cmd)

    SMU.instr.write(':TRIGger:DIGital5:OUT:PULSewidth 0.02')
    for i in range(0, 30):
        SMU.instr.write('*TRG')
        time.sleep(0.2)
    exit()

    SMU.instr.write(':DIGital:LINE5:MODE TRIG, OUT')
    SMU.instr.write(':TRIGger:DIGital5:OUT:PULSewidth 0.01')

    SMU.instr.write(':TRIGger:DIGital5:OUT:STIMulus COMMAND')
    print('*')
    print(SMU.instr.query(':TRIGger:DIGital5:OUT:STIMulus?'))
    print('*')

    SMU.instr.write('*TRG')

    exit()
    SMU.instr.write(':DIGital:LINE5:MODE DIGital, OUT')
    SMU.instr.write(':DIGital:LINE5:STATE 0')
    time.sleep(0.1)
    SMU.instr.write(':DIGital:LINE5:STATE 1')
    time.sleep(0.025)
    SMU.instr.write(':DIGital:LINE5:STATE 0')
    exit()

    # for i in range(1, 7):
    i = 5
    for _ in range(0, 1000):
        SMU.instr.write(':DIGital:LINE{}:STATE 0'.format(i))
        time.sleep(0.02)
        SMU.instr.write(':DIGital:LINE{}:STATE 1'.format(i))
        time.sleep(0.005)

    # time.sleep(0.5)
    # SMU.instr.write(':DIGital:LINE2:STATE 1')
    exit()

    SMU.set_source_function('i', source_range=1e-2)
    SMU.set_sense_function('v', sense_range=0)
    # SMU.set_voltage_limit(2)
    # SMU.set_sense_function('v', sense_range=2)
    # SMU.source.set_current(0)

    # print(SMU.remote_sense(True))

    # buffer = 'gate_data'
    # buffer = 'iv_data'

    SMU.set_voltage(0)
    SMU.output_state(True)

    SMU.set_integration_time(1)

    # print('NPLC')
    # print(SMU.scpi_comm(':SENSE:CURRENT:NPLCYCLES?'))
    # print(SMU.scpi_comm(':SENSE:VOLTAGE:NPLCYCLES?'))
    # print(SMU.scpi_comm(':SENSE:CURRENT:NPLCYCLES 0.1'))
    # print(SMU.scpi_comm(':SENSE:VOLTAGE:NPLCYCLES 0.1'))

    for i in range(0, 1000):
        print()
        SMU.trigger_measurement()
        # time.sleep(0.15)
        t = time.time()
        latest = SMU.read_latest()
        dt = time.time() - t
        print(latest, dt)
    exit()

    current = 1e-2
    print(SMU.set_sense_function(function='i', sense_range=0))
    print(SMU.set_source_function(function='v', source_range=current))
    print(SMU.set_current_limit(current=current))
    print(SMU.set_sense_function(function='i', sense_range=current))
    exit()
    print(SMU.set_source_function(function='v', source_range=1.7))
    print(SMU.set_sense_function(function='i', sense_range=0.14))
    exit()

    print('klaf')
    for i in range(0, 10):
        print(i)
        SMU.set_voltage(i * 0.1)
        SMU.trigger_measurement('gate_data')
        print(SMU.read_latest('gate_data'))
        time.sleep(0.25)
    exit()
    # print(print(SMU.configure_measurement_function('i')))
    SMU.trigger_measurement('gate_data')
    print(SMU.read_latest('gate_data'))
    exit()
    print(print(SMU.configure_measurement_function('i')))
    print()
    for i in range(0, 10):
        SMU.trigger_measurement('iv_data')
        print(SMU.read_latest('iv_data'))

    exit()

    SMU.set_source_function('v')
    SMU.set_current_limit(1e-3)

    SMU.set_voltage(0.001)

    for i in range(0, 20):
        SMU.set_voltage(0.001 * i)
        SMU.trigger_measurement('iv_data')
        print(SMU.read_latest('iv_data'))
    exit()
