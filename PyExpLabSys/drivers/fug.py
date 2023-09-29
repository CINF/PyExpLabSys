# pylint: disable=invalid-name
"""Driver for \"fug NTN 140 - 6,5 17965-01-01\" power supply
    Communication via the Probus V serial interface.

    Written using the two documents:

    1) Interface system Probus V - Documentation for RS232/RS422
       Revision of document 2.4
    2) Probus V - Command Reference
       Base Module
       ADDAT30 Firmware PIC0162 V4.0
       Version of Document V2.22

    Should be freely available from
    http://www.fug-elektronik.de/en/support/download.html
    (Available  August 25 2017)
"""

from __future__ import print_function
import sys
import time
import serial

# Error codes and their interpretations as copied from manuals
ERRORCODES = {
    'E0': 'no error',
    'E1': 'no data available',
    'E2': 'unknown register type',
    'E4': 'invalid argument',
    'E5': 'argument out of range',
    'E6': 'register is read only',
    'E7': 'Receive Overflow',
    'E8': 'EEPROM is write protected',
    'E9': 'adress error',
    'E10': 'unknown SCPI command',
    'E11': 'not allowed Trigger-on-Talk',
    'E12': 'invalid argument in ~Tn command',
    'E13': 'invalid N-value',
    'E14': 'register is write only',
    'E15': 'string too long',
    'E16': 'wrong checksum',
}


class FUGNTN140Driver(object):
    """Driver for fug NTN 140 power supply

    **Methods**

    * **Private**

      * __init__
      * _check_answer
      * _flush_answer
      * _get_answer
      * _write_register
      * _read_register

    * **Public**

      * reset()
      * stop()
      * is_on()
      * output(state=True/False)
      * get_state()
      * identification_string()
      * ---
      * set_voltage(value)
      * get_voltage()
      * monitor_voltage()
      * ramp_voltage(value, program=0)
      * ramp_voltage_running()
      * ---
      * set_current(value)
      * get_current()
      * monitor_current()
      * ramp_current(value, program=0)
      * ramp_current_running()

    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        port='/dev/ttyUSB0',
        baudrate=9600,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        device_reset=True,
        V_max=6.5,
        I_max=10,
    ):
        """Initialize object variables

        For settings port, baudrate, parity, stopbits, bytesize, see
        the pyserial documentation.

        Args:
            device_reset (bool): If true, resets all device parameters to
                default values

        """

        # Open a simple serial connection to port
        timeout_counter = 0
        while timeout_counter < 10:
            timeout_counter += 1
            self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                parity=parity,
                stopbits=stopbits,
                bytesize=bytesize,
                timeout=1,
            )
            time.sleep(1)
            try:
                if self.ser.isOpen():
                    break
            except AttributeError:
                print('Attempt #{}\n'.format(timeout_counter))
        else:
            print('Connection timeout')
            sys.exit()
        # End character
        self.end = '\x00'
        if not self.ser.isOpen():
            raise IOError('Connection to device is not open')
        else:
            print('Connected to device: {}'.format(self.identification_string()))
        if device_reset:
            self.reset()
        self.V_max = V_max
        self.I_max = I_max

    # Answer string handling
    def _check_answer(self):
        """Verify correct answer string (neglect previous answers) """

        string = self.ser.readline()
        if string.decode('ascii').strip() == 'E0':
            return True
        else:
            self.stop()
            raise IOError(string.strip() + ' : ' + ERRORCODES[string.strip()])

    def _flush_answer(self, print_answer=False):
        """Flush answer bytes in waiting (should probably not be used) """

        if print_answer:
            while self.ser.inWaiting() > 0:
                print(repr(self.ser.read(1)))
        else:
            self.ser.read(self.ser.inWaiting())

    def _get_answer(self):
        """Get waiting answer string """

        string = self.ser.readline()
        string = string.decode('ascii')
        return string

    # Register handlers
    def _write_register(self, register, value):
        """Alters the value of a register """

        command = '>' + register + ' ' + str(value) + self.end
        self.ser.write(command.encode())
        self._check_answer()

    def _read_register(self, register, value_type=float):
        """Queries a register and returns its value """

        command = '>' + register + '?' + self.end
        self.ser.write(command.encode())
        string = self._get_answer()
        if value_type == float:
            # Interpret answer as 'float'
            return float(string.split(register + ':')[-1])
        elif value_type == int:
            # Interpret answer as 'int'
            return int(string.split(register + ':')[-1])
        elif value_type == str:
            # Return entire answer string
            return string
        elif value_type == bool:
            # Interpret answer as 'boolean' (through 'int')
            return bool(int(string.split(register + ':')[-1]))
        else:
            raise TypeError('Wrong input value_type')

    # Termination functions
    def reset(self):
        """Resets device """

        command = '=' + self.end
        self.ser.write(command.encode())
        self._check_answer()

    def stop(self, reset=True):
        """Closes device properly before exit """

        if reset:
            self.reset()
        self.ser.close()

    # Output interpreters
    def is_on(self):
        """Checks if output is ON (>DON)
        Returns True if ON
        """

        return self._read_register('DON', bool)

    def output(self, state=False):
        """Set output ON (>BON) """

        if state is True:
            register = 'F1'
        elif state is False:
            register = 'F0'
        command = register + self.end
        self.ser.write(command.encode())
        self._check_answer()

    def get_state(self):
        """Checks whether unit is in CV or CC mode (>DVR/>DIR) """

        if self._read_register('DVR', bool):
            return 'CV'
        elif self._read_register('DIR', bool):
            return 'CC'
        else:
            return 'No regulation mode detected'

    def identification_string(self):
        """Output serial number of device"""

        return self._read_register('CFN', str)

    # Voltage interpreters
    def set_voltage(self, value):
        """Sets the voltage (>S0) """

        # Minimum voltage
        if value < 0.0:
            value = 0.0
        # Maximum voltage
        if value > self.V_max:
            value = self.V_max
        self._write_register('S0', value)

    def get_voltage(self):
        """Reads the set point voltage (>S0A) """

        return self._read_register('S0A', float)

    def monitor_voltage(self):
        """Reads the actual (monitor) voltage (>M0) """

        V = self._read_register('M0', float)
        # Correct analog zero
        if V < 1e-3:
            V = 0.0
        return V

    def ramp_voltage(self, value, program=0):
        """Activates ramp function for voltage
        value : ramp value in volts/second (>S0R)

        +---------+--------------------------------------------------------------------+
        | program | setvalue behaviour                                                 |
        +=========+====================================================================+
        | 0       | (default) no ramp function. Setpoint is implemented immediately    |
        +---------+--------------------------------------------------------------------+
        | 1       | >S0A follows the value in >S0 with the adjusted ramp rate          |
        |         | upwards and downwards                                              |
        +---------+--------------------------------------------------------------------+
        | 2       | >S0A follows the value in >S0 with the adjusted ramp rate only     |
        |         | upwards. When programming downwards, >S0A follows >S0 immediately. |
        +---------+--------------------------------------------------------------------+
        | 3       | >S0A follows the value in >S0 with a special ramp function only    |
        |         | upwards. When programming downwards, >S0A follows >S0 immediately. |
        |         | Ramp between 0..1 with 11.11E-3 per second. Above 1 : with >S0R    |
        +---------+--------------------------------------------------------------------+
        | 4       | Same as 2, but >S0 as well as >S0A are set to zero if >DON is 0    |
        +---------+--------------------------------------------------------------------+

        """

        if program != -1:
            self._write_register('S0B', program)
        self._write_register('S0R', value)

    def ramp_voltage_running(self):
        """Return status of voltage ramp.
        True: still ramping
        False: ramp complete
        """

        return self._read_register('S0S', bool)

    # Current interpreters
    def set_current(self, value):
        """Sets the current (>S1) """

        # Minimum current
        if value < 0:
            value = 0
        # Maximum current
        if value > self.I_max:
            value = self.I_max
        # Set current
        self._write_register('S1', value)

    def get_current(self):
        """Reads the set point current (>S1A) """

        return self._read_register('S1A', float)

    def monitor_current(self):
        """Reads the actual (monitor) current (>M1) """

        I = self._read_register('M1', float)
        # Correct analog zero
        if I < 1e-3:
            I = 0.0
        return I

    def ramp_current(self, value, program=0):
        """Activates ramp function for current.
        See ramp_voltage() for description."""

        if program != -1:
            self._write_register('S1B', program)
        self._write_register('S1R', value)

    def ramp_current_running(self):
        """Return status of current ramp.
        True: still ramping
        False: ramp complete
        """

        return self._read_register('S1S', bool)

    def read_H1(self, ret=False):
        """Read H1 FIXME not yet done"""

        t0 = time.time()
        command = '>H1?' + self.end
        self.ser.write(command.encode())
        bytes_ = self.ser.read(36)
        bytes_ = bytes_[3:-1].decode()
        # Byte 01
        voltage = (
            int.from_bytes(bytes.fromhex(bytes_[0:4]), byteorder='little')
            / 65535
            * 12.5
        )
        # Byte 23
        current = (
            int.from_bytes(bytes.fromhex(bytes_[4:8]), byteorder='little') / 65535 * 8
        )
        if ret is True:
            return voltage, current
        # Byte 4
        print('Byte 4: ', end='')
        byte = bytes.fromhex(bytes_[8:10])
        bits = bin(int.from_bytes(byte, byteorder='big'))[2:].zfill(2)
        print(bits)
        print(
            'Power supply is {}digitally controlled'.format(
                'not ' if bits[-1] == '0' else ''
            )
        )
        print(
            'Power supply is {}analogue controlled'.format(
                'not ' if bits[-2] == '0' else ''
            )
        )
        print(
            'Power supply is {}in calibration mode'.format(
                'not ' if bits[-3] == '0' else ''
            )
        )
        print('X-STAT: {}'.format(bits[-4]))
        print('3-REG: {}'.format(bits[-5]))
        print('Output is {}'.format('ON' if bits[-6] == '1' else 'OFF'))
        if bits[:2] == '01':
            mode = 'is in CV mode'
        elif bits[:2] == '10':
            mode = 'is in CC mode'
        elif bits[:2] == '00':
            mode = 'is not regulated'
        elif bits[:2] == '11':
            mode = 'appears to be in both CV and CC mode'
        print('Power supply {}'.format(mode))
        # Byte 5
        print('Byte 5: ', end='')
        byte = bytes.fromhex(bytes_[10:12])
        bits = bin(int.from_bytes(byte, byteorder='big'))[2:].zfill(8)
        print(bits)
        print(
            'Polarity of voltage: {}'.format(
                'positive' if bits[-1] == '0' else 'negative'
            )
        )
        print(
            'Polarity of current: {}'.format(
                'positive' if bits[-2] == '0' else 'negative'
            )
        )

        print()
        # UNUSED 6789
        # Byte 10 11 12 13
        print('Serial number: ', end='')
        byte = bytes.fromhex(bytes_[20:28])
        print(int.from_bytes(byte, byteorder='big'))
        # Byte 14
        byte = bytes.fromhex(bytes_[28:30])
        code = int.from_bytes(byte, byteorder='big')
        print('Last error code: {}\n'.format(code))
        print('{:6.4} V  -  {:6.4} A   '.format(voltage, current))
        # while self.ser.inWaiting() > 0:
        #    bytes_.append(self.ser.read(1))
        # bytes_.append(self.ser.read(32)
        print('Command time: {} s'.format(time.time() - t0))
        return bytes_

    def print_states(self, t0=0):
        """Print the current state of the power supply"""
        t = time.time()
        V = self.monitor_voltage()
        I = self.monitor_current()
        state = self.get_state()
        deltat = time.time() - t
        print(
            '{:8.2f} s ; {:>6.2f} W ; {:>8.4} V ; {:>8.4} A ; {:4.3f} s ; {}'.format(
                t - t0, V * I, V, I, deltat, state
            )
        )


def test():
    """Module test function"""
    try:
        power = FUGNTN140Driver(port='/dev/ttyUSB2', device_reset=True)
        return power
        power.output(True)
        power.ramp_current(value=0.2, program=1)
        power.ramp_voltage(value=0.2, program=1)
        t0 = time.time()
        power.print_states(t0)
        power.set_voltage(3)
        return
        power.set_current(2.5)
        while power.ramp_voltage_running():
            power.print_states(t0)
        print('Ramp criteria fulfilled')
        power.ramp_voltage(0)
        power.ramp_current(0)
        power.set_voltage(6.5)
        power.set_current(3.5)
        for _ in range(10):
            time.sleep(0.8)
            power.print_states(t0)
        power.set_current(4.5)
        for _ in range(10):
            time.sleep(0.8)
            power.print_states(t0)
        power.stop()
    except KeyboardInterrupt:
        power.stop()


if __name__ == '__main__':
    ps = test()
