# pylint: disable=C0301,R0904, C0103

"""
Self contained module to run a SPECS sputter gun including fall-back text gui
"""

import serial
import time
import threading
import curses


class CursesTui(threading.Thread):
    """ Defines a fallback text-gui for the source control. """
    def __init__(self, sputtergun):
        threading.Thread.__init__(self)
        self.sc = sourcecontrol
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.screen.keypad(1)
        self.screen.nodelay(1)
        self.time = time.time()

    def run(self):
        while True:
            self.screen.addstr(3, 2, 'X-ray Source Control')

            if self.sc.status['degas']:
                self.screen.addstr(4, 2, "Degassing")

            if self.sc.status['remote']:
                self.screen.addstr(5, 2, "Remote control")

            if self.sc.status['standby']:
                self.screen.addstr(6, 2, "Device status: Standby  ")

            if self.sc.status['operate']:
                self.screen.addstr(6, 2, "Device status: Operate! ")

            try:
                self.screen.addstr(9, 2, "Filament bias: {0:.3f}V          ".format(self.sc.status['filament_bias']))
                self.screen.addstr(10, 2, "Filament Current: {0:.2f}A          ".format(self.sc.status['filament_current']))
                self.screen.addstr(11, 2, "Emission Current: {0:.4f}mA          ".format(self.sc.status['emission_current']))
                self.screen.addstr(12, 2, "anode Voltage: {0:.2f}V          ".format(self.sc.status['anode_voltage']))
                self.screen.addstr(13, 2, "anode Power: {0:.2f}W          ".format(self.sc.status['anode_power']))
            except ValueError:
                #self.screen.addstr(9, 2, "Temperature, electronics: -                   ")
                self.screen.addstr(10, 2, "emission Current: -                           ")
                self.screen.addstr(11, 2, "Filament bias: -                             ")
                self.screen.addstr(12, 2, "Filament Current: -                          ")
                self.screen.addstr(13, 2, "Emission current: -                          ")
                self.screen.addstr(14, 2, "Acceleration Voltage: -                      ")

            #self.screen.addstr(16, 2, "Latest error message: " + self.sc.status['error'])

            self.screen.addstr(17, 2, "Runtime: {0:.0f}s       ".format(time.time() - self.time))
            self.screen.addstr(18, 2, 'q: quit, s: standby, o: operate')

            n = self.screen.getch()
            if n == ord('q'):
                self.sc.running = False
            # disable s o key
            #if n == ord('s'):
            #    self.sc.goto_standby = True
            #if n == ord('o'):
            #    self.sc.goto_operate = True

            self.screen.refresh()
            time.sleep(1)

    def stop(self):
        """ Cleanup the terminal """
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()


class XRC1000(threading.Thread):
    """ Driver for X-ray Source Control - XRC 1000"""

    def __init__(self, ):
        """ Initialize module

        Establish serial connection and create status variable to
        expose the status for the instrument for the various gui's
        """
        threading.Thread.__init__(self)

        #self.simulate = simulate
        self.f = serial.Serial('/dev/ttyUSB0', 9600, timeout=0.25)
        #baud: 9600, bits: 8, parity: None
        self.f.write('SERNO?' + '\r')  # Echo off
        time.sleep(1)
        # ID test
        return_string = self.f.read(self.f.inWaiting())
        if return_string == 'SERNO:000003AADEBD28'+chr(10)+chr(62):
            pass
        else:
            print('Error SERIAL Number: ' + return_string)
            print(len(return_string))
            print(len('SERNO:000003AADEBD28\n>'))
            for el in return_string:
                print(ord(el))
        self.status = {}  # Hold parameters to be accecible by gui
        self.status['hv'] = None
        self.status['standby'] = None
        self.status['operate'] = None
        self.status['degas'] = None
        self.status['remote'] = None
        self.status['error'] = ''
        #self.status['temperature'] = None
        self.status['sputter_current'] = None
        self.status['filament_bias'] = None
        self.status['filament_current'] = None
        self.status['emission_current'] = None
        self.status['anode_voltage'] = None
        self.running = True
        self.goto_standby = False
        self.goto_operate = False
        self.simulate = False
        #self.update_status()

    def comm(self, command):
        """ Communication with the instrument

        Implements the synatx need to send commands to instrument including
        handling carrige returns and extra lines of 'OK' and other
        pecularities of the instrument.

        :param command: The command to send
        :type command: str
        :return: The reply to the command striped for protocol technicalities
        :rtype: str
        
        posible comands,REM, LOC, REM?, IEM 20e-3, IEM?, UAN 10e3, UAN?, IHV?, IFI?, UFI?, PAN?. SERNO?, OFF, COOL, STAN, UAON, OPE, OPE?, ANO 1, ANO 2, ANO?, STAT?,
        """
        n = self.f.inWaiting()
        if n > 1:
            print('Error')
        else:
            self.f.read(n)
        self.f.write(command + '\r')
        time.sleep(0.1)
        reply = self.f.readline()
        #print(reply)
        self.f.read(1)  # Empty buffer for extra newline
        time.sleep(0.1)

        #ok_reply = self.f.readline()  # Wait for OK

        #cr_count = reply.count('\r')
        #Check that no old commands is still in buffer and that the reply
        #is actually intended for the requested parameter
        #cr_check = cr_count == 1
        command_check = reply[0:len(command) - 1] == command.strip('?')
        #ok_check = ok_reply.find('OK') > -1
        #print(cr_check)
        #print(command_check)
        #print(ok_check)
        if command_check:# and ok_check:
            echo_length = len(command)
            return_string = reply[echo_length:]
        elif(command == 'os'):
            return_string = reply
        #else:
        #    if self.simulate is False:
        #        return_string = 'Communication error!'
        #    else:
        #        return(1)
        return(return_string)

    def read_emission_current(self): #need testing
        """ Read the emission current. Unit mA
        :return: The emission current
        :rtype: float
        """
        reply = self.comm('IEM?') # 'IEM 20e-3\r'
        #print(reply)
        try:
            value = float(reply)
        except ValueError:
            self.status['error'] = reply
            value = None
        return(value)

    def read_filament_voltage(self): #need testing
        """ Read the filament voltage. Unit V
        :return: The filament voltage
        :rtype: float
        """
        reply = self.comm('UFI?')
        try:
            value = float(reply) / 1.0
        except ValueError:
            self.status['error'] = reply
            value = None
        return(value)

    def read_filament_current(self): #need testing
        """ Read the filament current. Unit A
        :return: The filament current
        :rtype: float
        """
        reply = self.comm('IFI?')
        try:
            value = float(reply) / 1.0
        except ValueError:
            self.status['error'] = reply
            value = None
        return(value)

    #def read_emission_current(self):
    #    """ Read the emission current. Unit mA
    #    :return: The emission current
    #    :rtype: float
    #    """
    #    reply = self.comm('ec?')
    #    try:
    #        value = float(reply) / 1000
    #    except ValueError:
    #        self.status['error'] = reply
    #        value = None
    #    return(value)

    def read_anode_voltage(self): #need testing
        """ Read the anode voltage. Unit kV
        :return: The anode voltage
        :rtype: float
        """
        reply = self.comm('UAN?')
        try:
            value = float(reply) / 1.0
        except ValueError:
            self.status['error'] = reply
            value = None
        return(value)
        
    def read_anode_power(self): #need testing
        """ Read the anode voltage. Unit kV
        :return: The anode voltage
        :rtype: float
        """
        reply = self.comm('PAN?')
        try:
            value = float(reply) / 1.0
        except ValueError:
            self.status['error'] = reply
            value = None
        return(value)

    def standby(self):#need testing
        """ Set the device on standby
        The function is not working entirely as intended.
        TODO: Implement check to see if the device is alrady in standby
        :return: The direct reply from the device
        :rtype: str
        """
        reply = self.comm('STAN')
        return(reply)

    def operate(self):#need testing
        """ Set the device in operation mode
        TODO: This function should only be activated from standby!!!
        :return: The direct reply from the device
        :rtype: str
        """
        reply = self.comm('OPE')
        return(reply)

    def remote_enable(self, local=False):#need testing
        """ Enable or disable remote mode
        :param local: If True the device is set to local, otherwise to remote
        :type local: Boolean
        :return: The direct reply from the device
        :rtype: str
        """
        if local:
            reply = self.comm('LOC')
        else:
            reply = self.comm('REM')
        return(reply)

    def update_status(self): # not done
        """ Update the status of the instrument

        Runs a number of status queries and updates self.status

        :return: The direct reply from the device
        :rtype: str
        """

        #self.status['temperature'] = self.read_temperature_energy_module()
        self.status['filament_bias'] = self.read_filament_voltage()
        self.status['filament_current'] = self.read_filament_current()
        self.status['emission_current'] = self.read_emission_current()
        self.status['anode_voltage'] = self.read_anode_voltage()
        self.status['anode_power'] = self.read_anode_power()

        """reply = self.comm('os').lower()
        if self.simulate is not True:
            hv = None
        else:
            hv = False
        if reply.find('he') > -1:
            hv = False
        if reply.find('ha') > -1:
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

        if reply.find('op') > -1:
            self.status['operate'] = True
        else:
            self.status['operate'] = False
        #!TODO: Update status to also accept neither operate or standby

        if reply.find('dg') > -1:
            self.status['degas'] = True
        else:
            self.status['degas'] = False"""

        return(reply)

    def run(self):
        while self.running:
            time.sleep(0.5)
            self.update_status()
            if self.goto_standby:
                self.standby()
                self.goto_operate = False
                self.goto_standby = False
            if self.goto_operate:
                self.operate()
                self.goto_operate = False

if __name__ == '__main__':
    sc = XRC1000()
    #print sc.read_emission_current()
    #print sc.read_filament_voltage()
    #print sc.read_filament_current()
    #print sc.read_anode_voltage()
    #print sc.read_anode_power()

    print sc.comm('REM?')
    print sc.comm('SERNO?')
    print sc.comm('IHV?')
    print sc.comm('OPE?')
    print sc.comm('ANO?')
    print sc.comm('STAT?')
    #sourcecontrol.start()

    #tui = CursesTui(sputter)
    #tui.daemon = True
    #tui.start()

    #print('Temperature: ' + str(sputter.read_temperature_energy_module()))
    #print('Sputter current: ' + str(sputter.read_sputter_current()))
    #print('Temperature: ' + str(sputter.read_temperature_energy_module()))
    print('Filament voltage: ' + str(sc.read_filament_voltage()))
    print('Filament current: ' + str(sc.read_filament_current()))
    print('Emission current: ' + str(sc.read_emission_current()) + 'A')
    print('Anode voltage: ' + str(sc.read_anode_voltage()))
    print('Anode power: ' + str(sc.read_anode_power()) + 'W')

    #sputter.update_status()
    #print('Enable:')
    #print(sputter.remote_enable(local=False))
    #print('Status:')
    #print(sputter.status)
