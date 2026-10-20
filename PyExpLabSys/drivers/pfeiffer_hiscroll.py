""" Driver for Edwards, nXDS pumps """
import time
import logging
import serial

import pathlib
import json

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())


class PfeifferHiscroll(object):
    """Driver for the Pfeiffer Hiscrool series of dry pumps"""

    def __init__(self, port: str, device_address: int):
        self.device_address = str(device_address).zfill(3)
        self.ser = serial.Serial(port, 9600, timeout=1.0)
        time.sleep(0.1)

    def _checksum(self, cmd: str) -> str:
        crc_sum = 0
        for c in cmd:
            crc_sum = crc_sum + ord(c)
        crc = crc_sum % 256
        crc_str = str(crc).zfill(3)
        return crc_str

    def comm(self, action: str, parameter: str, command: str) -> str:
        """Ensures correct protocol for instrument"""
        cmd_len = str(len(command)).zfill(2)
        crc_command = self.device_address + action + '0' + parameter + cmd_len + command
        crc = self._checksum(crc_command)
        final_command = crc_command + crc + '\r\n'

        self.ser.write(final_command.encode('ascii'))
        reply = self.ser.read_until(b'\r').decode().strip()
        reply_crc = self._checksum(reply[:-3])
        if not reply.endswith(reply_crc):
            print('CRC error in reply!')
            print('Reply was:')
            print(reply)
            raise Exception('CRC error in reply!')

        expected = self.device_address + '10' + parameter
        assert reply.startswith(expected)
        payload = reply[len(expected) :]
        length = int(payload[0:2])
        value = payload[2 : 2 + length]
        return value

    def _format_as_data_type(self, data_type, data):
        """Utility function to convert data to representations understood by RS485"""
        if data_type == 10:
            # 9.9E-2 would be represented as 990018 (the last two digits is
            # is the exponent subtracted by 20)
            s = '{:1.1E}'.format(data)
            exp = str(int(s[-3:]) + 20).zfill(2)
            return s[0] + s[2] + '00' + exp
        if data_type == 2:
            s = '{:2.2f}'.format(data)
            return (s[:-3] + s[-2:]).zfill(6)
        if data_type == 0:
            if data:
                return '111111'
            return '000000'

    def _format_from_data_type(self, data_type, data):
        if data_type == 10:
            exp = int(data[-2:]) - 20
            decimals = int(data[: len(data) - 2]) / 1000
            return decimals * 10 ** exp
        if data_type == 2:
            return float(data[:4] + '.' + data[4:])
        if data_type == 0:
            if data == '111111':
                return True
            elif data == '000000':
                return False
            raise ValueError('{} not a valid boolean'.format(data))

    def rotational_speed(self):
        """Current rotational speed of the pump in Hz"""
        # cmd = '02=?'
        cmd = '=?'

        # Setpint, parameter 308 will return value in Hz
        raw = self.comm(action='0', parameter='397', command=cmd)
        setpoint = int(raw) / 60.0

        # Actual, parameter 309 will return value in Hz
        raw = self.comm(action='0', parameter='398', command=cmd)
        actual = int(raw) / 60.0

        # Nominal speed
        raw = self.comm(action='0', parameter='399', command=cmd)
        nominal = int(raw) / 60.0

        return_dict = {'actual': actual, 'setpoint': setpoint, 'nominal': nominal}
        return return_dict

    # Does not exist for edwards_nxds
    def drive_power(self):
        """Drive power in W, current in A, voltage in V"""
        cmd = '=?'

        # Current
        raw = self.comm(action='0', parameter='310', command=cmd)
        current = int(raw) / 100  # d-type float

        # Voltage
        raw = self.comm(action='0', parameter='313', command=cmd)
        voltage = int(raw) / 100  # d-type float

        # Power
        raw = self.comm(action='0', parameter='316', command=cmd)
        power = int(raw)

        return_dict = {'voltage': voltage, 'current': current, 'power': power}
        return return_dict

    # Compatible with edwards_nxds
    def read_pump_type(self):
        """Read identification information"""
        cmd = '=?'

        # Firmware version
        firmware = self.comm(action='0', parameter='312', command=cmd)
        name = self.comm(action='0', parameter='349', command=cmd)
        product_number = self.comm(action='0', parameter='388', command=cmd).strip()
        raw = self.comm(action='0', parameter='399', command=cmd)
        drive_serial = self.comm(action='0', parameter='355', command=cmd).strip()
        nominal = int(raw) / 60.0
        return {
            'type': name,
            'software': firmware,
            'nominal_frequency': nominal,
            'drive_serial': drive_serial,
            'product_number': product_number,
        }

    # Compatible with edwards_nxds, which has fields 'pump' and 'controller'
    def read_pump_temperature(self):
        """Read Pump Temperature"""
        cmd = '=?'

        # Final Stage Temperature
        raw = self.comm(action='0', parameter='324', command=cmd)
        final_stage = int(raw)

        # Electroncs temperature (controller)
        raw = self.comm(action='0', parameter='326', command=cmd)
        electronics = int(raw)

        # Motor temperature (pump)
        raw = self.comm(action='0', parameter='346', command=cmd)
        motor = int(raw)

        r_dict = {'pump': motor, 'controller': electronics, 'final_stage': final_stage}
        return r_dict

    # Common with edwards_nxds
    def read_serial_numbers(self):
        """Pfeiffer does not yet store the serial number in a parameter, but a unique
        number can still be obtained"""
        cmd = '=?'
        # The serial number of the drive unit is stored in param 355
        return self.comm(action='0', parameter='355', command=cmd)

    # Common with edwards_nxds
    def read_run_hours(self):
        """Return number of run hours"""
        cmd = '=?'
        raw = int(self.comm(action='0', parameter='311', command=cmd))
        run_hours = int(raw)
        return run_hours

    # def set_run_state(self, on_state):
    #     """ Start or stop the pump """
    #     if on_state is True:
    #         return_string = self.comm('!C802 1')
    #     else:
    #         return_string = self.comm('!C802 0')
    #     return return_string

    # This does not exists for HiScroll, but could propaply be calculated
    # from run hours and known service intervals
    def bearing_service(self):
        return 0

    def config_acc(self, channel, value=None):
        """Configure accessory channels C1 and D1 (will automatically detect inputs"""
        cfg = {
            6: 'Output always "0"',
            7: 'Output always "1"',
            15: 'Gas ballast valve',
            16: 'Vacuum safety valve, type IV 16 M',
            17: 'Pressure sensor',
            18: 'Vacuum safety valve, type ISV 25',
        }
        # Default to print info on both channels
        if value is None:
            if channel.upper().startswith('C'):
                state = int(self.comm(action='0', parameter='068', command='=?'))
                return state, cfg[state]
            if channel.upper().startswith('D'):
                state = int(self.comm(action='0', parameter='069', command='=?'))
                return state, cfg[state]

        cmd = str(value).zfill(3)
        if channel.upper().startswith('C'):
            param = '068'
        if channel.upper().startswith('D'):
            param = '069'
        self.comm(action='1', parameter=param, command=cmd)

    def config_digital_out(self, channel, value=None):
        """Returns or sets the configuration for the two digital outputs (channel 1 and 2)"""
        cfg = {
            0: 'Switch-point reached',
            1: 'No error',
            2: 'Error',
            5: 'Set rotation speed reached',
            6: 'Pump on',
            9: 'Always "0"',
            10: 'Always "1"',
            11: 'Remote priority active',
            21: 'Gas ballast',
        }
        if value is None:
            if int(channel) == 1:
                state = int(self.comm(action='0', parameter='024', command='=?'))
            if int(channel) == 2:
                state = int(self.comm(action='0', parameter='019', command='=?'))
            return state, cfg[state]

        cmd = str(value).zfill(3)
        if int(channel) == 1:
            self.comm(action='1', parameter='024', command=cmd)
        if int(channel) == 2:
            self.comm(action='1', parameter='019', command=cmd)

    def config_digital_in(self, value=None):
        """Returns or sets the configuration for the digital inpur"""
        cfg = {
            0: 'Deactivated',
            1: 'Deactivated',
            2: 'Deactivated',
            3: 'Deactivated',
            4: 'Deactivated',
            5: 'Rotation speed setting mode activated',
        }
        if value is None:
            state = int(self.comm(action='0', parameter='063', command='=?'))
            return state, cfg[state]

        cmd = str(value).zfill(3)
        self.comm(action='1', parameter='063', command=cmd)

    # def pump_controller_status(self):
    #     """ Read  the status of the pump controller """
    #     return_string = self.comm('?V813')
    #     status = return_string.split(';')
    #     controller_run_time = int(status[0])
    #     time_to_service = int(status[1])
    #     return {'controller_run_time': controller_run_time,
    #             'time_to_service': time_to_service}

    # def read_normal_speed_threshold(self):
    #     """ Read the value for acknowledge the pump as normally running """
    #     return_string = self.comm('?S804')
    #     return int(return_string)

    # def read_standby_speed(self):
    #     """ Read the procentage of full speed on standby """
    #     return_string = self.comm('?S805')
    #     return int(return_string)

    # def read_pump_status(self):
    #     """ Read the overall status of the pump """
    #     return_string = self.comm('?V802')
    #     status = return_string.split(';')
    #     rotational_speed = int(status[0])
    #     system_status_1 = self.status_to_bin(status[1])
    #     messages = []
    #     if system_status_1[15] is True:
    #         messages.append('Decelerating')
    #     if system_status_1[14] is True:
    #         messages.append('Running')
    #     if system_status_1[13] is True:
    #         messages.append('Standby Active')
    #     if system_status_1[12] is True:
    #         messages.append('Above normal Speed')
    #     # if system_status_1[11] is True: # It is not entirely clear what this
    #     #    messages.append('Above ramp speed') # message means
    #     if system_status_1[5] is True:
    #         messages.append('Serial interface enabled')

    #     system_status_2 = self.status_to_bin(status[2])
    #     if system_status_2[15] is True:
    #         messages.append('At power limit!')
    #     if system_status_2[14] is True:
    #         messages.append('Acceleration limited')
    #     if system_status_2[13] is True:
    #         messages.append('Deceleration limited')
    #     if system_status_2[11] is True:
    #         messages.append('Time for service!')
    #     if system_status_2[9] is True:
    #         messages.append('Warning')
    #     if system_status_2[8] is True:
    #         messages.append('Alarm')
    #     warnings = []
    #     warning_status = self.status_to_bin(status[3])
    #     if warning_status[14] is True:
    #         warnings.append('Temperature too low')
    #     if warning_status[9] is True:
    #         warnings.append('Pump too hot')
    #     if warning_status[5] is True:
    #         warnings.append('Temperature above maxumum measureable value')
    #     if warning_status[0] is True:
    #         warnings.append('EEPROM problem - service needed!')
    #     faults = []
    #     fault_status = self.status_to_bin(status[4])
    #     if fault_status[14] is True:
    #         faults.append('Voltage too high')
    #     if fault_status[13] is True:
    #         faults.append('Current too high')
    #     if fault_status[12] is True:
    #         faults.append('Temperature too high')
    #     if fault_status[11] is True:
    #         faults.append('Temperature sensor fault')
    #     if fault_status[10] is True:
    #         faults.append('Power stage failure')
    #     if fault_status[7] is True:
    #         faults.append('Hardware latch fault')
    #     if fault_status[6] is True:
    #         faults.append('EEPROM problem')
    #     if fault_status[4] is True:
    #         faults.append('No parameter set')
    #     if fault_status[3] is True:
    #         faults.append('Self test fault')
    #     if fault_status[2] is True:
    #         faults.append('Serial control interlock')
    #     if fault_status[1] is True:
    #         faults.append('Overload time out')
    #     if fault_status[0] is True:
    #         faults.append('Acceleration time out')
    #     return {'rotational_speed': rotational_speed, 'messages': messages,
    #             'warnings': warnings, 'faults': faults}

    # This does not exists for HiScroll, but could propaply be calculated
    # from run hours and known service intervals
    def read_service_status(self):
        return []

    # def set_standby_mode(self, standbymode):
    #     """ Set the pump on or off standby mode """
    #     if standbymode is True:
    #         return_string = self.comm('!C803 1')
    #     else:
    #         return_string = self.comm('!C803 0')
    #     return return_string

    """ Does not exist for edwards_nxds """

    def pressure_setpoint(self, setpoint: float = None):
        """Setpoint Pressure in hPa"""
        if setpoint is None:
            cmd = '=?'
            reply = self.comm(action='0', parameter='730', command=cmd)
            return self._format_from_data_type(10, reply)

        if type(setpoint) == str and len(setpoint) == 6:
            cmd = setpoint
        else:
            if setpoint < 0.01:
                setpoint = 0.01
            elif setpoint > 30:
                setpoint = 30
            cmd = self._format_as_data_type(10, setpoint)
        raw = self.comm(action='1', parameter='730', command=cmd)
        return raw

    """ Does not exist for edwards_nxds """

    def pressure(self):
        """Pressure in hPa"""
        cmd = '=?'
        raw = self.comm(action='0', parameter='740', command=cmd)
        exp = int(raw[-2:]) - 20
        decimals = int(raw[: len(raw) - 2]) / 1000
        pressure = decimals * 10 ** exp
        if pressure == 0:
            name = self.comm(action='0', parameter='739', command=cmd)
            if name == 'noSens':
                print('No gauge connected at C1')
                return None
        return pressure

    """ Does not exist for edwards_nxds """

    def standby(self, standby: bool = None):
        """Alias for stand_by"""
        return self.stand_by(standby)

    def stand_by(self, stand_by: bool = None):
        if stand_by is None:
            cmd = '=?'
            raw = self.comm(action='0', parameter='002', command=cmd)
            actual_stand_by = False
            if raw == '111111':
                actual_stand_by = True
            return actual_stand_by

        if stand_by:
            cmd = '111111'
        else:
            cmd = '000000'
        self.comm(action='1', parameter='002', command=cmd)

        """ Does not exist for edwards_nxds """

    def pressure_mode(self, pressure_mode: bool = None):
        if pressure_mode is None:
            cmd = '=?'
            raw = self.comm(action='0', parameter='020', command=cmd)
            actual_pressure_mode = False
            if raw == '111111':
                actual_pressure_mode = True
            return actual_pressure_mode

        if pressure_mode:
            cmd = '111111'
        else:
            cmd = '000000'
        self.comm(action='1', parameter='020', command=cmd)

    def speed_mode(self, speed_mode: bool = None):
        if speed_mode is None:
            cmd = '=?'
            raw = self.comm(action='0', parameter='026', command=cmd)
            actual_speed_mode = False
            if raw == '111111':
                actual_speed_mode = True
            return actual_speed_mode

        if speed_mode:
            cmd = '111111'
        else:
            cmd = '000000'
        self.comm(action='1', parameter='020', command=cmd)

    def gas_ballast(self, value=None):
        """Switch gas ballast on/off"""
        if value is None:
            reply = bool(self.comm(action='0', parameter='052', command='=?'))
            return reply
        if value:
            cmd = '111111'
        else:
            cmd = '000000'
        self.comm(action='1', parameter='052', command=cmd)

    def vent_mode(self, value=None):
        """Vent valve mode"""
        if value is None:
            return int(self.comm(action='0', parameter='030', command='=?'))

        cmd = str(value).zfill(3)
        self.comm(action='1', parameter='030', command=cmd)

    def valve_mode(self, value=None):
        """Alias for vent_mode"""
        if value is None:
            return self.vent_mode(value)
        self.vent_mode(value)

    def auto_boost(self, on=None):
        """Enable/disable auto boost function"""
        if on is None:
            reply = self.comm(action='0', parameter='011', command='=?')
            return self._format_from_data_type(0, reply)

        cmd = self._format_as_data_type(0, on)
        self.comm(action='1', parameter='011', command=cmd)

    def auto_start(self, on=None):
        """Enable/disable auto start function"""
        if on is None:
            reply = self.comm(action='0', parameter='034', command='=?')
            return self._format_from_data_type(0, reply)

        cmd = self._format_as_data_type(0, on)
        self.comm(action='1', parameter='034', command=cmd)

    def address(self, address=None):
        """Set or read the RS485 address"""

        # Query address
        if address is None:
            reply = self.comm(action='0', parameter='797', command='=?')
            return int(reply)

        # Set address
        if address < 1:
            address = 1
        if address > 255:
            address = 255
        cmd = str(address).zfill(6)
        reply = self.comm(action='1', parameter='797', command=cmd)
        if reply == cmd:
            self.device_address = str(address).zfill(3)

    def setpoint_speed(self, value=None):
        """Set speed value in speed setting mode"""
        if value is None:
            reply = self.comm(action='0', parameter='707', command='=?')
            return self._format_from_data_type(2, reply)

        if value < 40:
            value = 40
        elif value > 100:
            value = 100
        cmd = self._format_as_data_type(2, value)
        self.comm(action='1', parameter='707', command=cmd)

    def setpoint_standby(self, value=None):
        """Set standby value in standby operation mode"""
        if value is None:
            reply = self.comm(action='0', parameter='717', command='=?')
            return self._format_from_data_type(2, reply)

        if value < 40:
            value = 40
        elif value > 100:
            value = 100
        cmd = self._format_as_data_type(2, value)
        self.comm(action='1', parameter='717', command=cmd)

    def valve_duration(self, value=None):
        """Set duration of gas ballast valve (minutes)"""
        # Note - does not seem to actually be data type 2, but just an integer
        if value is None:
            reply = self.comm(action='0', parameter='721', command='=?')
            return int(reply)

        if value < 0:
            value = 0
        elif value > 60:
            value = 60
        cmd = str(int(value)).zfill(6)
        self.comm(action='1', parameter='721', command=cmd)

    def setpoint_pressure(self, value=None):
        """Pressure setpoint at which auto standby switches on or the pressure auto
        regulates to (mbar)"""
        if value is None:
            reply = self.comm(action='0', parameter='730', command='=?')
            return self._format_from_data_type(10, reply)

        if value < 0.01:
            value = 0.01
        elif value > 30:
            value = 30
        cmd = self._format_as_data_type(10, value)
        self.comm(action='1', parameter='730', command=cmd)

    def valve_mode_threshold(self, value=None):
        """Pressure switching threshold (mbar) for the gas ballast valve in valve mode"""
        if value is None:
            reply = self.comm(action='0', parameter='731', command='=?')
            return self._format_from_data_type(10, reply)

        if value < 9e-2:
            value = 9e-2
        elif value > 30:
            value = 30
        cmd = self._format_as_data_type(10, value)
        self.comm(action='1', parameter='731', command=cmd)

    def auto_standby_threshold(self, value=None):
        """Switch-off threshold with auto standby - pressure (mbar)"""
        if value is None:
            reply = self.comm(action='0', parameter='732', command='=?')
            return self._format_from_data_type(10, reply)

        if value < 1:
            value = 1
        elif value > 100:
            value = 100
        cmd = self._format_as_data_type(10, value)
        self.comm(action='1', parameter='732', command=cmd)

    def pressure_correction_factor(self, value=None):
        """Correction factor for the pressure gauge"""
        if value is None:
            reply = self.comm(action='0', parameter='742', command='=?')
            return self._format_from_data_type(2, reply)

        if value == 0:
            return
        if value < 0.1:
            value = 0.1
        elif value > 8:
            value = 8
        cmd = self._format_as_data_type(2, value)
        self.comm(action='1', parameter='742', command=cmd)

    def copy_configuration(self, filename=None):
        """Load all configuration parameters and save to file if given - otherwise return"""
        cfg = {
            'address': None,
            'auto_boost': None,
            'digital_out_2': None,
            'digital_out_1': None,
            'pressure_mode': None,
            'speed_set_mode': None,
            'vent_mode': None,
            'auto_start': None,
            'digital_input_2': None,
            'setpoint_speed': None,
            'setpoint_standby': None,
            'valve_duration': None,
            'setpoint_pressure': None,
            'valve_mode_threshold': None,
            'auto_standby_threshold': None,
            'pressure_correction_factor': None,
            'C1': None,
            'D1': None,
        }
        # Should params 060 and 061 also be read?
        cfg['address'] = self.address()
        cfg['auto_boost'] = self.auto_boost()
        cfg['digital_out_2'] = self.config_digital_out(2)[0]
        cfg['digital_out_1'] = self.config_digital_out(1)[0]
        cfg['pressure_mode'] = self.pressure_mode()
        cfg['speed_set_mode'] = self.speed_mode()
        cfg['vent_mode'] = self.vent_mode()
        cfg['auto_start'] = self.auto_start()
        cfg['digital_input_2'] = self.config_digital_in()[0]
        cfg['setpoint_speed'] = self.setpoint_speed()
        cfg['setpoint_standby'] = self.setpoint_standby()
        cfg['valve_duration'] = self.valve_duration()
        cfg['setpoint_pressure'] = self.setpoint_pressure()
        cfg['valve_mode_threshold'] = self.valve_mode_threshold()
        cfg['auto_standby_threshold'] = self.auto_standby_threshold()
        cfg['pressure_correction_factor'] = self.pressure_correction_factor()
        cfg['C1'] = self.config_acc('C1')  # Won't be loaded
        cfg['D1'] = self.config_acc('D1')  # Won't be loaded

        # Return to user
        if filename is None:
            return cfg

        # or save to file
        filename = pathlib.Path(filename)
        with open(filename, 'w') as f:
            f.write(json.dumps(cfg))

    def load_configuration(self, filename):
        filename = pathlib.Path(filename)
        if not filename.exists():
            raise ValueError('"{}" does not exist'.format(filename.resolve()))
        with open(filename, 'r') as f:
            cfg = json.loads(f.readline())

        # Backup configuration
        info = self.read_pump_type()
        backup = pathlib.Path('{}.cfg.backup'.format(info['drive_serial']))
        self.copy_configuration(backup)

        # Apply settings
        for key, value in cfg.items():
            if key == 'address':
                self.address(value)
            if key == 'auto_boost':
                self.auto_boost(value)
            if key == 'digital_out_2':
                self.config_digital_out(2, value)
            if key == 'digital_out_1':
                self.config_digital_out(1, value)
            if key == 'pressure_mode':
                self.pressure_mode(value)
            if key == 'speed_set_mode':
                self.speed_mode(value)
            if key == 'vent_mode':
                self.vent_mode(value)
            if key == 'auto_start':
                self.auto_start(value)
            if key == 'digital_input_2':
                self.config_digital_in(value)
            if key == 'setpoint_speed':
                self.setpoint_speed(value)
            if key == 'setpoint_standby':
                self.setpoint_standby(value)
            if key == 'valve_duration':
                self.valve_duration(value)
            if key == 'setpoint_pressure':
                self.setpoint_pressure(value)
            if key == 'valve_mode_threshold':
                self.valve_mode_threshold(value)
            if key == 'auto_standby_threshold':
                self.auto_standby_threshold(value)
            if key == 'pressure_correction_factor':
                self.pressure_correction_factor(value)

    def errors(self):
        """Print basic error information"""
        # Overtemperatures
        ot_elec = self.comm(action='0', parameter='304', command='=?')
        ot_pump = self.comm(action='0', parameter='305', command='=?')
        # Error history
        error1 = self.comm(action='0', parameter='360', command='=?')
        error2 = self.comm(action='0', parameter='361', command='=?')
        error3 = self.comm(action='0', parameter='362', command='=?')

        # Print information
        print('Excess temperatures of..')
        print('Electronic drive: {}'.format(ot_elec))
        print('Pump: {}'.format(ot_pump))
        print(self.read_pump_temperature())
        print('Error history:\n{}\n{}\n{}'.format(error1, error2, error3))

    def run(self, value=None):
        """Switch pump on/off or read current state"""
        if value is None:
            reply = self.comm(action='0', parameter='010', command='=?')
            return self._format_from_data_type(0, reply)

        cmd = self._format_as_data_type(0, value)
        self.comm(action='1', parameter='010', command=cmd)


if __name__ == '__main__':
    PUMP = PfeifferHiscroll('/dev/ttyUSB0', device_address=2)
    print('Pump type: ', PUMP.read_pump_type())
    print('Pump temperatures: ', PUMP.read_pump_temperature())
    print('Run hours: ', PUMP.read_run_hours())
    print('Serial number: ', PUMP.read_serial_numbers())
    print(PUMP.config_acc('C'))
    print(PUMP.config_acc('D'))
    print(PUMP.config_digital_out(1))
    print(PUMP.config_digital_out(2))

    speed = PUMP.rotational_speed()
    print('Set rotational speed: ', speed['setpoint'])
    print('Actual rotational speed: ', speed['actual'])

    print('Pressure mode state: ', PUMP.pressure_mode())
    print('Pressure: ', PUMP.pressure())
