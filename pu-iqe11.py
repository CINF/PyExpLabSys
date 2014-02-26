import serial
import time


class Puiqe11:
    """ Driver for ion sputter guns from SPECS """

    def __init__(self):
        """ Initialize module

        Establish serial connection and create status variable to
        expose the status for the instrument for the various gui's
        """

        self.f = serial.Serial(0, 1200, timeout=1)
        self.f.write('e0' + '\r') #Echo off
        time.sleep(1)
        ok = self.f.read(self.f.inWaiting())
        if ok.find('OK') > -1:
            pass
        else:
            print('ERROR!!!')
        self.status = {}  # Hold parameters to be accecible by gui
        self.status['hv'] = False
        self.status['standby'] = False
        self.status['degas'] = False
        self.status['remote'] = False
        self.update_status()

    def comm(self, command):
        """ Communication with the instrument

        Implements the synatx need to send commands to instrument including
        handling carrige returns and extra lines of 'OK' and other
        pecularities of the instrument.

        :param command: The command to send
        :type command: str
        :return: The reply to the command striped for protocol technicalities
        :rtype: str
        """
        n = self.f.inWaiting()
        if n > 1:
            print('Error')
        else:
            self.f.read(n)
        self.f.write(command + '\r')
        reply = self.f.readline()
        self.f.read(1)  # Empty buffer for extra newline
        ok_reply = self.f.readline()  # Wait for OK
        cr_count = reply.count('\r')
        #Check that no old commands is still in buffer and that the reply
        #is actually intended for the requested parameter
        cr_check = cr_count == 1
        command_check = reply[0:len(command)-1] == command.strip('?')
        ok_check = ok_reply.find('OK') > -1
        if cr_check and command_check and ok_check:
            echo_length = len(command)
            return_string = reply[echo_length:]
        elif(command == 'os'):
            return_string = reply
        else:
            return_string = 'Communication error!'
        return(return_string)

    def read_sputter_current(self):
        """ Read the sputter current. Unit mA
        :return: The sputter current
        :rtype: float
        """
        reply = self.comm('eni?')
        value = float(reply)/1000
        return(value)

    def read_filament_voltage(self):
        """ Read the filament voltage. Unit V
        :return: The filament voltage
        :rtype: float
        """
        reply = self.comm('fu?')
        value = float(reply)/100.0
        return(value)

    def read_filament_current(self):
        """ Read the filament current. Unit A
        :return: The filament current
        :rtype: float
        """
        reply = self.comm('fi?')
        value = float(reply)/10.0
        return(value)

    def read_emission_current(self):
        """ Read the emission current. Unit mA
        :return: The emission current
        :rtype: float
        """
        reply = self.comm('ec?')
        value = float(reply)
        return(value)

    def read_acceleration_voltage(self):
        """ Read the acceleration voltage. Unit V
        :return: The acceleration voltage
        :rtype: float
        """
        reply = self.comm('ec?')
        value = float(reply)
        return(value)

    def read_temperature_energy_module(self):
        """ Read the temperature of the electronics module
        This value is not extremely correct, use only as guideline.
        :return: The temperature
        :rtype: float
        """
        reply = self.comm('ent?')
        value = float(reply)
        return(value)

    def standby(self):
        """ Set the device on standby
        The function is not working entirely as intended.
        TODO: Implement check to see if the device is alrady in standby
        :return: The direct reply from the device
        :rtype: str
        """
        reply = self.comm('sb')
        return(reply)

    def remote_enable(self, local=False):
        """ Enable or disable remote mode
        :param local: If True the device is set to local, otherwise to remote
        :type local: Boolean
        :return: The direct reply from the device
        :rtype: str
        """
        if local:
            reply = self.comm('lo')
        else:
            reply = self.comm('re')
        return(reply)

    def update_status(self):
        """ Update the status of the instrument

        Runs a number of status queries and updates self.status

        :return: The direct reply from the device
        :rtype: str
        """

        reply = self.comm('os').lower()
        hv = None
        if reply.find('ha') > -1:
            hv = False
        if reply.find('hv') > -1:
            hv = True
        assert(hv is True or hv is False)
        self.status['hv'] = hv

        if reply.find('re') > -1:
            self.status['remote'] = True
        else:
            self.status['remote'] = False

        if reply.find('sb') > -1:
            self.status['standby'] = True
        else:
            self.status['standby'] = False

        if reply.find('dg') > -1:
            self.status['degas'] = True
        else:
            self.status['degas'] = False

        return(reply)

if __name__ == '__main__':
    sputter = Puiqe11()
    """
    print('Sputter current: ' + str(sputter.read_sputter_current()))
    print('Temperature: ' + str(sputter.read_temperature_energy_module()))
    print('Temperature: ' + str(sputter.read_temperature_energy_module()))
    print('Filament voltage: ' + str(sputter.read_filament_voltage()))
    print('Filament current: ' + str(sputter.read_filament_current()))
    print('Emission current: ' + str(sputter.read_emission_current()))
    print('Acceleration voltage: ' + str(sputter.read_acceleration_voltage()))
    """
    #print('Enable:')
    #print(sputter.remote_enable(local=False))
    #print('Status:')
    print(sputter.status)
