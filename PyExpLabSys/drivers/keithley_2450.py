"""
Simple driver for Keithley 2450 SMU
"""
import time
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

    # def measure_range(self, function: str, meas_range: float = None):
    #     if function.lower() == 'i':
    #         scpi_function = 'CURRENT'
    #     elif function.lower() == 'v':
    #         scpi_function = 'VOLTAGE'
    #     else:
    #         raise Exception('Function not allowed: {}'.format(function))
    #     cmd = 'SENSE:{}:RANGE'.format(scpi_function)
        
    #     if meas_range == 0:
    #         self.instr.write(cmd + ':AUTO ON')
    #     elif meas_range is not None:
    #         self.instr.write(cmd + ':AUTO OFF')
    #         self.instr.write(cmd + ' {}'.format(meas_range))

    #     actual_auto = (self.instr.query(cmd + ':AUTO?').find('1') > -1)
    #     actual_range = float(self.instr.query(cmd + '?'))
    #     return (actual_auto, actual_range)
    
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
        cmd = ':TRACE:TRIGGER "{}"; *TRG;'.format(buffer)
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
        actual_readings = self.elements_in_buffer(buffer)
        if actual_readings > 0:
            self.instr.write(':TRACE:CLEAR "{}"'.format(buffer))
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
                t = time.time()
                raw = self.instr.query(cmd)
                # print('k2540 raw read', time.time() - t, '   ', self.latest_fetch_time)
                reading = self._parse_raw_reading(raw)
                # print(reading)
                if reading is None:
                    continue
                dt = reading['delta_time']
            except ValueError:
                pass
        self.latest_fetch_time = dt
        return reading

    def configure_digital_port_as_triggers(self, channel_list=[]):
        """
        Configure the DB9 digital output to be configured as
        individual outputs, that can be (mis)used as triggers.
        """
        # Manual trigger of lines can be achived like this:
        # :DIGital:LINE{}:MODE DIGITAL, OUT'
        # :DIGital:LINE{}:STATE 0
        # time.sleep(0.1)
        # :DIGital:LINE{}:STATE 1
        # time.sleep(0.025)
        # :DIGital:LINE{}:STATE 0
        if not channel_list:
            channel_list = [1, 2, 3, 4, 5, 6]
        for i in range(1, 7):
            if i in channel_list:
                cmd = ':DIGital:LINE{}:MODE TRIG, OPENdrain'.format(i)
                self.instr.write(cmd)
                print(cmd)
                cmd = ':TRIGger:DIGital{}:OUT:PULSewidth 1e-5'.format(i)
                self.instr.write(cmd)
                cmd = ':TRIGger:DIGital{}:OUT:STIMulus COMMAND'.format(i)
                self.instr.write(cmd)
            else:
                cmd = ':DIGital:LINE{}:MODE DIGItal, IN'.format(i)
                self.instr.write(cmd)
                print(cmd)

if __name__ == '__main__':
    import time

    SMU = Keithley2450(interface='lan', device='192.168.0.30')
    print(SMU.measure_range('i'))
    exit()
    
    SMU.configure_digital_port_as_triggers([1, 2, 3, 4, 5, 6])

    time.sleep(10)
    SMU.instr.write('*RST')
    trigger_list = [
        1,  # Vxy - white
        2,  # DMM - brown
        3,  # Vxx - Green
        4,  # Osciloscope - Yellow
    ]
    SMU.configure_digital_port_as_triggers(trigger_list)

    t = time.time()
    SMU.trigger_measurement()
    print(time.time() - t)
    # SMU.instr.write('*TRG')
    # print(time.time() - t)
    exit()

    # SMU.configure_digital_port_as_triggers()
    # SMU.clear_buffer()
    for i in range(0, 100):
        SMU.trigger_measurement()
        SMU.instr.write('*TRG')
        # SMU.instr.assert_trigger()
        # time.sleep(0.1)
    exit()

    while True:
        time.sleep(1.5)
        print('Trig')
        SMU.instr.trigger_measurement()
        # SMU.instr.write('*TRG')
        # print(SMU.read_latest())
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
