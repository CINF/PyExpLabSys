""" Driver for Edwards, nXDS pumps """
import time
import logging
import serial

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
        # print(crc_command)
        final_command = crc_command + crc + '\r\n'

        self.ser.write(final_command.encode('ascii'))
        reply = self.ser.read_until(b'\r').decode().strip()
        reply_crc = self._checksum(reply[:-3])
        if not reply.endswith(reply_crc):
            print('CRC error in reply!')
            print('Reply was:')
            print(reply)
            raise Exception('CRC error in reply!')

        start_index = reply.find(parameter)
        payload = reply[start_index + len(parameter) :]
        length = int(payload[0:2])
        value = payload[2 : 2 + length]
        return value

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

        raw = self.comm(action='0', parameter='399', command=cmd)
        nominal = int(raw) / 60.0
        return {'type': name, 'software': firmware, 'nominal_frequency': nominal}

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
        """Apparently HiScroll cannot read serial from rs485"""
        return 'HiSroll'

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
            raw = self.comm(action='0', parameter='730', command=cmd)
            exp = int(raw[-2:]) - 20
            decimals = int(raw[: len(raw) - 2]) / 1000
            pressure_setpoint = decimals * 10**exp
            return pressure_setpoint

        cmd = '990018'
        raw = self.comm(action='1', parameter='730', command=cmd)
        return raw

    """ Does not exist for edwards_nxds """

    def pressure(self):
        """Pressure in hPa"""
        cmd = '=?'
        raw = self.comm(action='0', parameter='740', command=cmd)
        exp = int(raw[-2:]) - 20
        decimals = int(raw[: len(raw) - 2]) / 1000
        pressure = decimals * 10**exp
        return pressure

    """ Does not exist for edwards_nxds """

    def stand_by_state(self, stand_by: bool = None):
        if stand_by is None:
            cmd = '=?'
            raw = self.comm(action='0', parameter='002', command=cmd)
            if raw.find('00000') > 0:
                actual_stand_by = False
            if raw.find('11111') > 0:
                actual_stand_by = True
            return actual_stand_by

        if stand_by:
            cmd = '111111'
        else:
            cmd = '000000'
        raw = self.comm(action='1', parameter='002', command=cmd)
        # todo: Consider some error checking here
        return stand_by

        """ Does not exist for edwards_nxds """

    def pressure_mode_state(self, pressure_mode: bool = None):
        if pressure_mode is None:
            cmd = '=?'
            raw = self.comm(action='0', parameter='020', command=cmd)
            print(raw)
            if raw.find('00000') > -1:
                actual_pressure_mode = False
            if raw.find('11111') > -1:
                actual_pressure_mode = True
            return actual_pressure_mode

        if pressure_mode:
            cmd = '111111'
        else:
            cmd = '000000'
        raw = self.comm(action='1', parameter='020', command=cmd)
        # todo: Consider some error checking here
        return pressure_mode


if __name__ == '__main__':
    PUMP = PfeifferHiscroll('/dev/ttyUSB0', device_address=2)

    # print('Set rotaional speed: ', PUMP.set_rotational_speed())
    # print('Actual rotaional speed: ', PUMP.actual_rotational_speed())

    # print(PUMP.stand_by_state(True))
    # print('Stand by state: ', PUMP.stand_by_state(False))
    print('Pressure mode state: ', PUMP.pressure_mode_state())
    print('Pressure mode state: ', PUMP.pressure_mode_state(True))
    print('Pressure: ', PUMP.pressure())
    print('Pressure setpoint: ', PUMP.pressure_setpoint())
    print('Pressure setpoint: ', PUMP.pressure_setpoint(1))
    print('Pressure setpoint: ', PUMP.pressure_setpoint())

    # print(PUMP.stand_by_state(False))
    for i in range(0, 5):
        print('Pressure: ', PUMP.pressure())
        time.sleep(0.5)
    print('Rotaional speed: ', PUMP.rotational_speed())
    print('Power: ', PUMP.drive_power()['power'])

    print()
    print()
    exit()
    # Edwards compatible commands
    print('Pump type: ', PUMP.read_pump_type())
    print(PUMP.read_pump_temperature())
    # print(PUMP.read_serial_numbers())
    print('Run hours: ', PUMP.read_run_hours())
    # print(PUMP.read_normal_speed_threshold())
    # print(PUMP.read_standby_speed())
    # print(PUMP.pump_controller_status())
    # print(PUMP.bearing_service())
    # print(PUMP.read_pump_status()['rotational_speed'])
    # print(PUMP.set_run_state(True))
    # print(PUMP.set_standby_mode(False))
