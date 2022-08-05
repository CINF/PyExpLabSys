""" Simple driver for Keithley 6220 SMU """
import time
from PyExpLabSys.drivers.scpi import SCPI


class Keithley6220(SCPI):
    """
    Simple driver for Keithley 6200 SMU
    Actual implementation performed on a 6221 - please
    double check if you have a 6220.
    """

    def __init__(self, interface, hostname='', device='',
                 baudrate=9600, gpib_address=None):
        if interface == 'serial':
            SCPI.__init__(self, interface=interface, device=device,
                          baudrate=baudrate, line_ending='\n')
            self.comm_dev.timeout = 2
            self.comm_dev.rtscts = False
            self.comm_dev.xonxoff = False
        if interface == 'lan':
            SCPI.__init__(self, interface=interface, hostname=hostname)
        if interface == 'gpib':
            SCPI.__init__(self, interface=interface, gpib_address=gpib_address)

        self.latest_error = []
        # Set error format to binary:
        self.scpi_comm('FORMAT:SREGISTER BINARY')
        self.clear_error_queue()

    def _check_register(self, command: str, msg=None):
        magic_messages = {
            ('STATUS:QUESTIONABLE:EVENT?', 4): 'Questionable Power',
            ('STATUS:QUESTIONABLE:EVENT?', 8): 'Questionable Calibration',
            ('STATUS:MEASUREMENT:EVENT?', 2): 'Internal temperature too high',
            ('STATUS:MEASUREMENT:EVENT?', 3): 'Voltage complicance',
            ('*ESR?', 4): 'Setpoint out of current range'
        }
        if msg is None:
            msg = command
        register_ok = True
        status_string = self.scpi_comm(command)
        # Reverse string to count from 0 to N
        bit_string = status_string[::-1]
        for i in range(0, len(bit_string)):
            # print('{}: {}'.format(i, esr[i]))
            if bit_string[i] == '1':
                register_ok = False
                error_string = magic_messages.get((command, i))
                if error_string is None:
                    error_string = '{} error in bit: {}'.format(msg, i)
                self.latest_error.append(error_string)
        return register_ok

    def read_status(self):
        status_ok = True
        registers = {
            '*ESR?': 'Standard Event Status',
            # 'STATUS:MEASUREMENT:CONDITION?': 'Measurement Condition Register',
            '*STB?': 'Status Byte Register',
            'STATUS:MEASUREMENT:EVENT?': 'Measurement Event Register',
            'STATUS:QUESTIONABLE:EVENT?': 'Questionable Event Register'
        }
        for command, message in registers.items():
            status_ok = status_ok & self._check_register(command, message)

        # Operation Event Register - apparantly only available doing sweeps:
        # 'STATUS:OPERATON:EVENT?'

        # This seems to be a summary. If performance is a problem, it can be
        # used to check if other conditions needs to be checked.
        # Service Request Enable: '*SRE?'
        if status_ok:
            self.latest_error = []
        return status_ok

    def read_error_queue(self):
        error_list = {}
        error = 1
        while error > 0:
            next_error = self.scpi_comm('STATUS:QUEUE:NEXT?')
            error_raw, msg = next_error.split(',')
            error = int(error_raw)
            if error > 0:
                if error in error_list:
                    error_list[error]['count'] += 1
                else:
                    error_list[error] = {'count': 1, 'msg': msg}
        return error_list

    def output_state(self, output_state: bool = None):
        """ Turn the output on or off """
        if output_state is not None:
            if output_state:
                self.scpi_comm('OUTPUT ON')
            else:
                self.scpi_comm('OUTPUT OFF')
        actual_state_raw = self.scpi_comm('OUTPUT?')
        actual_state = int(actual_state_raw[0]) == 1
        return actual_state

    def set_current_range(self, current_range: float = None):
        """
        This device can only source current, not voltage
        """
        if current_range is not None:
            self.scpi_comm('CURRENT:RANGE {}'.format(current_range))
        actual_range_raw = self.scpi_comm('CURRENT:RANGE?')
        print(actual_range_raw)
        actual_range = float(actual_range_raw)
        return actual_range

    def set_voltage_limit(self, voltage: float = None):
        """ Set the desired voltate limit """
        if voltage is not None:
            self.scpi_comm('CURRENT:COMPLIANCE {:.9f}'.format(voltage))
        actual = self.scpi_comm('CURRENT:COMPLIANCE?')
        return actual

    def set_current(self, current: float):
        """ Set the DC current, when not performing a waveform """
        self.scpi_comm('CURRENT {:.9f}'.format(current))
        return True

    def source_sine_wave(self, frequency, amplitude):
        self.scpi_comm('SOUR:WAVE:FUNC SIN')
        self.scpi_comm('SOUR:WAVE:FREQ {}'.format(frequency))
        self.scpi_comm('SOUR:WAVE:AMPL {}'.format(amplitude))
        self.scpi_comm('SOUR:WAVE:OFFS 0')  # Offset
        # self.scpi_comm('SOUR:WAVE:PMAR:STAT OFF')  !!!! ‘ Turn off phase marker.
        self.scpi_comm('SOUR:WAVE:DUR:TIME INF')
        self.scpi_comm('SOUR:WAVE:RANG BEST')
        self.scpi_comm('SOUR:WAVE:ARM')
        self.scpi_comm('SOUR:WAVE:INIT')

    def stop_and_unarm(self):
        self.scpi_comm('SOUR:WAVE:ABOR')


if __name__ == '__main__':
    GPIB = 12
    SMU = Keithley6220(interface='gpib', gpib_address=GPIB)
    SMU.stop_and_unarm()
    print(SMU.read_status())

    print(SMU.set_voltage_limit(0.1))
    SMU.set_current_range(1e-4)
    SMU.set_current(1e-5)
    SMU.output_state(True)

    time.sleep(2)

    print(SMU.read_error_queue())
    print(SMU.read_status())
    print(SMU.read_error_queue())
    print(SMU.latest_error)
