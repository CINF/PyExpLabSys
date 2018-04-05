""" Driver for Edwards, nXDS pumps """
from __future__ import print_function
import time
import logging
import serial
from PyExpLabSys.common.supported_versions import python2_and_3
# Configure logger as library logger and set supported python versions
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
python2_and_3(__file__)

class EdwardsNxds(object):
    """ Driver for the Edwards nXDS series of dry pumps """

    def __init__(self, port):
        self.ser = serial.Serial(port, 9600, timeout=2)
        time.sleep(0.1)

    def comm(self, command):
        """ Ensures correct protocol for instrument """
        self.ser.write((command + '\r').encode('ascii'))
        return_string = self.ser.readline().decode()
        if not return_string[2:5] == command[2:5]:
            raise IOError
        return return_string[6:-1]

    def read_pump_type(self):
        """ Read identification information """
        return_string = self.comm('?S801')
        pump_type = return_string.split(';')
        return {'type': pump_type[0], 'software': pump_type[1],
                'nominal_frequency': pump_type[2]}

    def read_pump_temperature(self):
        """ Read Pump Temperature """
        return_string = self.comm('?V808')
        temperatures = return_string.split(';')
        pump = int(temperatures[0])
        controller = int(temperatures[1])
        return {'pump':pump, 'controller':controller}

    def read_serial_numbers(self):
        """ Read Pump Serial numbers """
        return_string = self.comm('?S835')
        service = return_string.split(';')
        serials = service[0].split(' ')
        return {'Pump SNs':serials[0], 'drive-module SN':serials[1],
                'PCA SN':serials[2], 'type':service[1].strip()}

    def read_run_hours(self):
        """ Return number of run hours """
        return_string = self.comm('?V810')
        run_hours = int(return_string)
        return run_hours

    def set_run_state(self, on_state):
        """ Start or stop the pump """
        if on_state is True:
            return_string = self.comm('!C802 1')
        else:
            return_string = self.comm('!C802 0')
        return return_string

    def status_to_bin(self, word):
        """ Convert status word to array of binaries """
        status_word = ''
        for i in range(0, 4):
            val = (int(word[i], 16))
            status_word += (bin(val)[2:].zfill(4))
        bin_word = [False] * 16
        for i in range(0, 15):
            bin_word[i] = (status_word[i] == '1')
        return bin_word

    def bearing_service(self):
        """ Status of bearings """
        return_string = self.comm('?V815')
        status = return_string.split(';')
        time_since = int(status[0])
        time_to = int(status[1])
        return {'time_since_service': time_since, 'time_to_service':time_to}

    def pump_controller_status(self):
        """ Read  the status of the pump controller """
        return_string = self.comm('?V813')
        status = return_string.split(';')
        controller_run_time = int(status[0])
        time_to_service = int(status[1])
        return {'controller_run_time': controller_run_time, 'time_to_service':time_to_service}

    def read_normal_speed_threshold(self):
        """ Read the value for acknowledge the pump as normally running """
        return_string = self.comm('?S804')
        return int(return_string)

    def read_standby_speed(self):
        """ Read the procentage of full speed on standby """
        return_string = self.comm('?S805')
        return int(return_string)

    def read_pump_status(self):
        """ Read the overall status of the pump """
        return_string = self.comm('?V802')
        status = return_string.split(';')
        rotational_speed = int(status[0])
        system_status_1 = self.status_to_bin(status[1])
        messages = []
        if system_status_1[15] is True:
            messages.append('Decelerating')
        if system_status_1[14] is True:
            messages.append('Running')
        if system_status_1[13] is True:
            messages.append('Standby Active')
        if system_status_1[12] is True:
            messages.append('Above normal Speed')
        #if system_status_1[11] is True: # It is not entirely clear what this
        #    messages.append('Above ramp speed') # message means
        if system_status_1[5] is True:
            messages.append('Serial interface enabled')

        system_status_2 = self.status_to_bin(status[2])
        if system_status_2[15] is True:
            messages.append('At power limit!')
        if system_status_2[14] is True:
            messages.append('Acceleration limited')
        if system_status_2[13] is True:
            messages.append('Deceleration limited')
        if system_status_2[11] is True:
            messages.append('Time for service!')
        if system_status_2[9] is True:
            messages.append('Warning')
        if system_status_2[8] is True:
            messages.append('Alarm')
        warnings = []
        warning_status = self.status_to_bin(status[3])
        if warning_status[14] is True:
            warnings.append('Temperature too low')
        if warning_status[9] is True:
            warnings.append('Pump too hot')
        if warning_status[5] is True:
            warnings.append('Temperature above maxumum measureable value')
        if warning_status[0] is True:
            warnings.append('EEPROM problem - service needed!')
        faults = []
        fault_status = self.status_to_bin(status[4])
        if fault_status[14] is True:
            faults.append('Voltage too high')
        if fault_status[13] is True:
            faults.append('Current too high')
        if fault_status[12] is True:
            faults.append('Temperature too high')
        if fault_status[11] is True:
            faults.append('Temperature sensor fault')
        if fault_status[10] is True:
            faults.append('Power stage failure')
        if fault_status[7] is True:
            faults.append('Hardware latch fault')
        if fault_status[6] is True:
            faults.append('EEPROM problem')
        if fault_status[4] is True:
            faults.append('No parameter set')
        if fault_status[3] is True:
            faults.append('Self test fault')
        if fault_status[2] is True:
            faults.append('Serial control interlock')
        if fault_status[1] is True:
            faults.append('Overload time out')
        if fault_status[0] is True:
            faults.append('Acceleration time out')
        return {'rotational_speed': rotational_speed, 'messages': messages,
                'warnings': warnings, 'faults': faults}

    def read_service_status(self):
        """ Read the overall status of the pump """
        service_status = self.status_to_bin(self.comm('?V826'))
        messages = []
        if service_status[15] is True:
            messages.append('Tip seal service is due')
        if service_status[14] is True:
            messages.append('Bearing service is due')
        if service_status[12] is True:
            messages.append('Controller service is due')
        if service_status[8] is True:
            messages.append('Service is due')
        return messages

    def set_standby_mode(self, standbymode):
        """ Set the pump on or off standby mode """
        if standbymode is True:
            return_string = self.comm('!C803 1')
        else:
            return_string = self.comm('!C803 0')
        return return_string

if __name__ == '__main__':
    PUMP = EdwardsNxds('/dev/ttyUSB3')
    #print(PUMP.read_pump_type())
    print(PUMP.read_pump_temperature())
    #print(PUMP.read_serial_numbers())
    #print(PUMP.read_run_hours())
    #print(PUMP.read_normal_speed_threshold())
    #print(PUMP.read_standby_speed())
    #print(PUMP.pump_controller_status())
    #print(PUMP.bearing_service())
    #print(PUMP.read_pump_status()['rotational_speed'])
    #print(PUMP.set_run_state(True))
    #print(PUMP.set_standby_mode(False))
