# pylint: disable=C0301,R0904, C0103

"""
Self contained module to run a SPECS sputter gun including fall-back text gui
"""

import serial
import time
import threading
import curses
import socket
import json

EXCEPTION = None
log = open('error_log.txt', 'w')


class CursesTui(threading.Thread):
    """ Defines a fallback text-gui for the source control. """
    def __init__(self, sourcecontrol):
        threading.Thread.__init__(self)
        self.sc = sourcecontrol
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.screen.keypad(1)
        self.screen.nodelay(1)
        self.time = time.time()
        self.countdown = False
        self.last_key = None
        self.running = True

    def run(self):
        while self.running:
            self.screen.addstr(3, 2, 'X-ray Source Control, ID:  ' + str(self.sc.status['ID']))

            if self.sc.status['degas']:
                self.screen.addstr(4, 2, "Degassing")

            if self.sc.status['remote']:
                self.screen.addstr(5, 2, "Control mode: Remote")
            else:
                self.screen.addstr(5, 2, "Control mode: Local")

            if self.sc.status['standby']:
                self.screen.addstr(6, 2, "Device status, Standby: ON  ")
            else:
                self.screen.addstr(6, 2, "Device status, Standby: OFF  ")
                
            if self.sc.status['hv']:
                self.screen.addstr(7, 2, "Device status: HV ON  ")
            else:
                self.screen.addstr(7, 2, "Device status: HV OFF  ")

            if self.sc.status['operate']:
                self.screen.addstr(8, 2, "Device status: Operate ON ")
            else:
                self.screen.addstr(8, 2, "Device status, Operate: OFF ")
            
            #if self.sc.status['error'] != None:
            #    self.screen.addstr(9, 2, "Error: " + str(self.sc.status['error']))

            try:
                self.screen.addstr(10, 2, "Filament bias: {0:.3f}V          ".format(self.sc.status['filament_bias']))
                self.screen.addstr(11, 2, "Filament Current: {0:.2f}A          ".format(self.sc.status['filament_current']))
                self.screen.addstr(12, 2, "Filament Power: {0:.2f}W          ".format(self.sc.status['filament_power']))
                self.screen.addstr(13, 2, "Emission Current: {0:.4f}A          ".format(self.sc.status['emission_current']))
                self.screen.addstr(14, 2, "Anode Voltage: {0:.2f}V          ".format(self.sc.status['anode_voltage']))
                self.screen.addstr(15, 2, "Anode Power: {0:.2f}W          ".format(self.sc.status['anode_power']))
                self.screen.addstr(16, 2, "Water flow: {0:.2f}L/min       ".format(self.sc.status['water_flow']))
            except Exception as exception:
                global EXCEPTION
                EXCEPTION = exception
                #self.screen.addstr(10,2, exception.message)
                self.screen.addstr(10, 2, "Filament bias: -                   ")
                self.screen.addstr(11, 2, "Filament Current: -                           ")
                self.screen.addstr(12, 2, "Filament Power: -                           ")
                self.screen.addstr(13, 2, "Emission Current: -                             ")
                self.screen.addstr(14, 2, "Anode Voltage: -                          ")
                self.screen.addstr(15, 2, "Anode Power: -                      ")
                self.screen.addstr(16, 2, "water flow: -                          ")
            if self.sc.status['error'] != None:
                self.screen.addstr(18, 2, "Latest error message: " + str(self.sc.status['error']) + " at time: " + str(self.sc.status['error time']))

            self.screen.addstr(19, 2, "Runtime: {0:.0f}s       ".format(time.time() - self.time))
            if self.countdown:
                self.screen.addstr(18, 2, "Time until shutdown: {0:.0f}s       ".format(self.countdown_end_time -time.time()))
                if time.time() > self.countdown_end_time:
                    self.sc.goto_off = True
                    self.countdown = False
            
            self.screen.addstr(21, 2, 'q: quit program, s: standby, o: operate, c: cooling, x: shutdown gun')
            self.screen.addstr(22, 2, ' 3: shutdown in 3h, r: change to remote')
            
            self.screen.addstr(24, 2, ' Latest key: ' + str(self.last_key))

            n = self.screen.getch()
            if n == ord('q'):
                self.sc.running = False
                self.running = False
                self.last_key = chr(n)
            elif n == ord('s'):
                self.sc.goto_standby = True
                self.last_key = chr(n)
            elif n == ord('o'):
                self.sc.goto_operate = True
                self.last_key = chr(n)
            elif n == ord('c'):
                self.sc.goto_cooling = True
                self.last_key = chr(n)
            elif n == ord('x'):
                self.sc.goto_off = True
                self.last_key = chr(n)
            elif n == ord('r'):
                self.sc.goto_remote = True
                self.last_key = chr(n)
            elif n == ord('3'):
                self.countdown = True
                self.countdown_end_time = float(time.time() + 3*3600.0) # second
                self.last_key = chr(n)
            
            # disable s o key
            #if n == ord('s'):
            #    self.sc.goto_standby = True
            #if n == ord('o'):
            #    self.sc.goto_operate = True

            self.screen.refresh()
            time.sleep(1)
        time.sleep(5)
        self.stop()
        print(EXCEPTION)

    def stop(self):
        """ Cleanup the terminal """
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()


class XRC1000(threading.Thread):
    """ Driver for X-ray Source Control - XRC 1000"""

    def __init__(self, port=None):
        """ Initialize module

        Establish serial connection and create status variable to
        expose the status for the instrument for the various gui's
        """
        threading.Thread.__init__(self)
        
        if port == None:
            port = '/dev/ttyUSB0'

        self.status = {}  # Hold parameters to be accecible by gui
        self.status['hv'] = None
        self.status['standby'] = None
        self.status['operate'] = None
        self.status['degas'] = None
        self.status['remote'] = None
        self.status['error'] = None
        self.status['error time'] = None
        self.status['start time'] = time.time()
        self.status['cooling'] = None
        self.status['off'] = None
        self.status['sputter_current'] = None
        self.status['filament_bias'] = None
        self.status['filament_current'] = None
        self.status['filament_power'] = None
        self.status['emission_current'] = None
        self.status['anode_voltage'] = None
        self.status['anode_power'] = None
        self.status['water_flow'] = None
        self.status['ID'] = None
        self.running = True
        self.goto_standby = False
        self.goto_operate = False
        self.goto_off = False
        self.goto_cooling = False
        self.goto_remote = False
        self.simulate = False
        #self.update_status()
        self.list_of_errors = []
        self.list_of_errors += ['>E251: Remote Locked !\n']
        self.list_of_errors += ['>E250: Not in Remote !\n']
        self.list_of_errors += ['>E251: Misplaced Query !\n']
        self.list_of_errors += ['>E251: Argument missing !\n']
        self.list_of_errors += ['>E251: Value to big or to low !\n']
        self.list_of_errors += ['>E251: Parameter unknown !\n']
        self.list_of_errors += ['>E251: Command not found !\n']
        self.list_of_errors += ['>E251: Unexpected Error code !\n']
        self.get_commands = ['REM?', 'IEM?', 'UAN?', 'IHV?', 'IFI?', 'UFI?', 'PAN?', 'SERNO?', 'ANO?', 'STAT?', 'OPE?']
        #self.simulate = simulate
        self.f = serial.Serial(port, 9600, timeout=0.25)
        #baud: 9600, bits: 8, parity: None
        return_string = self.comm('SERNO?')
        self.status['ID'] = return_string
        if self.status['ID'] == '000003AADEBD28':
            pass
        else:
            print('Error SERIAL Number: ' + return_string)
            print(len(return_string))
            print(len('SERNO:000003AADEBD28\n>'))
            for el in return_string:
                print(ord(el))
        self.get_status()
        if self.status['remote'] == False:
            self.remote_enable()
        self.get_status()
        self.init_socket()

    def init_socket(self,):
        self.address_port = ('rasppi00',9000)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def comm(self, command):
        """ Communication with the instrument

        Implements the synatx need to send commands to instrument including
        handling carrige returns and extra lines of 'OK' and other
        pecularities of the instrument.

        :param command: The command to send
        :type command: str
        :return: The reply to the command striped for protocol technicalities
        :rtype: str
        
        posible comands:
        REM?, IEM?, UAN?, IHV?, IFI?, UFI?, PAN?, SERNO?, ANO?, STAT?, OPE?
        REM, LOC, IEM 20e-3, UAN 10e3, OFF, COOL, STAN, UAON, OPE, ANO 1, ANO 2
        """
        n = self.f.inWaiting()
        if n > 1:
            print('Error')
            reply = self.f.read(n)
            self.status['error']='n = '+str(n) + ' ' + str(reply)
        else:
            self.f.read(n)
        self.f.write(command + '\r')
        time.sleep(0.2)
        reply = self.f.readline()
        #if '>' in reply[0]: # sanity character
        #    #print 'Valid command'
        #    pass
        #else:
        #    print 'None valid command/reply'
        #    print reply
        if command in self.get_commands and ':' in reply:
            echo, value = reply.split(':')
            return_string = value.strip()
            # get value from space to -2
            # posible answer to 'UAN?' true echo
            # '>UAN: 12.00e3\n'
            # posible answer to 'OPE?' non true echo
            # '>OPERATE: 4.000\n'
            #return_string = reply
        else:
            return_string = True
        return(return_string)
        
    def direct_comm(self, command):
        self.f.write(command + '\r')
        time.sleep(0.2)
        reply = self.f.readline()
        return_string = reply
        return(return_string)

    def read_water_flow(self,):
        """read the water flow from external hardware
        :return: water flow in L/min
        :rtype float
        """
        try:
            self.sock.sendto('stm312_xray_waterflow#json', self.address_port)
            answer = self.sock.recvfrom(1024)
            water_flow_time, water_flow = json.loads(answer[0])
        except:
            water_flow = -1.0
        return water_flow

    def read_emission_current(self): #need testing
        """ Read the emission current. Unit A
        :return: The emission current
        :rtype: float
        """
        reply = self.comm('IEM?') # 'IEM 20e-3\r'
        #print(reply)
        try:
            value = float(reply)/1.0
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
        """ Read the anode voltage. Unit V
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
        """ Read the anode voltage. Unit W
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
        #self.direct_comm('ANO 2')
        reply = self.comm('STAN')
        time.sleep(1)
        self.update_status()
        return(reply)

    def operate(self):#need testing
        """ Set the device in operation mode
        TODO: This function should only be activated from standby!!!
        :return: The direct reply from the device
        :rtype: str
        """
        #self.comm('ANO 2')
        #time.sleep(1)
        self.comm('UAN 12e3')
        time.sleep(1)
        self.comm('IEM 20e-3')
        time.sleep(1)
        reply = self.comm('OPE')
        self.update_status()
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
        time.sleep(1)
        self.update_status()
        return(reply)
    def change_control(self):#need testing
        """ Enable or disable remote mode
        :param local: If True the device is set to local, otherwise to remote
        :type local: Boolean
        :return: The direct reply from the device
        :rtype: str
        """
        if self.status['remote']:
            reply = self.comm('LOC')
        else:
            reply = self.comm('REM')
        time.sleep(1)
        self.update_status()
        return(reply)
        
    def cooling(self):
        """ Enable or disable water cooling
        :type local: Boolean
        :return: The direct reply from the device
        :rtype: str
        """
        reply = self.comm('COOL')
        self.update_status()
        return(reply)
        
    def get_status(self):
        reply = self.comm('STAT?')
        if reply[0:2] == '00':
            self.status['remote'] = False
        if reply[0:2] == '02':
            self.status['remote'] = True
            
        if reply[2:4] == '00':
            self.status['off'] = True
            self.status['cooling'] = False
            self.status['standby'] = False
            self.status['hv'] = False
            self.status['operate'] = False
        if reply[2:4] == '01':
            self.status['off'] = False
            self.status['cooling'] = True
            self.status['standby'] = False
            self.status['hv'] = False
            self.status['operate'] = False
        if reply[2:4] == '02':
            self.status['off'] = False
            self.status['cooling'] = False
            self.status['standby'] = True
            self.status['hv'] = False
            self.status['operate'] = False
        if reply[2:4] == '03':
            self.status['off'] = False
            self.status['cooling'] = False
            self.status['standby'] = False
            self.status['hv'] = True
            self.status['operate'] = False
        if reply[2:4] == '04':
            self.status['off'] = False
            self.status['cooling'] = False
            self.status['standby'] = False
            self.status['hv'] = False
            self.status['operate'] = True
        
        if reply[4:6] == '00':
            self.status['error'] = False
        else:
            if self.status['error'] == False:
                self.status['error time'] = time.time() - self.status['start time']
            self.status['error'] = reply[4:6]
            #error_bin = bin(int(reply[4:5]))
            #if error_bin[0:1] == ''
    def interlocks(self):
        self.status['interlocks'] = {'Failure':True,'HVLock':True,'Vacuum':True,'Water':True,'ERR_ILIM':True,'ERR_TOUT':True}
        
            
    
    def automated_operate(self):
        self.direct_comm('ANO 1')
        self.direct_comm('STAN')
        self.direct_comm('UAON')
        self.direct_comm('UAN 12e3') # 12kV
        self.direct_comm('OPE')
        wait = True
        n = 0
        while wait:
            if self.direct_comm('UAN?') == '>UAN: 12.00e3\n':
                wait = False
            elif n > 5:
                wait = False
            else:
                n+=1
                time.sleep(5)
        self.direct_comm('IEM 20e-3') # 20mA
        wait = True
        n = 0
        while wait:
            if self.direct_comm('IEM?') == '>IEM: 20.06e-3\n':
                wait = False
            elif n > 5:
                wait = False
            else:
                n+=1
                time.sleep(5)
        return True
    def turn_off(self):
        self.update_status()
        if self.status['operate']:
            self.comm('UAON')
            time.sleep(2)
            self.update_status()
        if self.status['hv']:
            self.comm('STAN')
            time.sleep(2)
            self.update_status()
        if self.status['standby']:
            self.comm('OFF')
            self.update_status()
        # Update key parameters
        return True

    def update_status(self): # not done
        """ Update the status of the instrument

        Runs a number of status queries and updates self.status

        :return: The direct reply from the device
        :rtype: str
        """

        #self.status['temperature'] = self.read_temperature_energy_module()
        self.status['filament_bias'] = self.read_filament_voltage()
        self.status['filament_current'] = self.read_filament_current()
        self.status['filament_power'] = self.status['filament_bias'] * self.status['filament_current']
        self.status['emission_current'] = self.read_emission_current()
        self.status['anode_voltage'] = self.read_anode_voltage()
        self.status['anode_power'] = self.read_anode_power()
        self.status['water_flow'] = self.read_water_flow()
        #log.write(str(self.status) + '\n')
        self.get_status()

        return(True)

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
            if self.goto_off:
                self.turn_off()
                self.goto_off = False
            if self.goto_cooling:
                self.cooling()
                self.goto_cooling = False
            if self.goto_remote:
                self.remote_enable(local=self.status['remote'])
                self.goto_remote = False
                



if __name__ == '__main__':
    sc = XRC1000(port='/dev/serial/by-id/usb-1a86_USB2.0-Ser_-if00-port0')
    #print sc.read_emission_current()
    #print sc.read_filament_voltage()
    #print sc.read_filament_current()
    #print sc.read_anode_voltage()
    #print sc.read_anode_power()
    #command_list=['REM?', 'IEM?', 'UAN?', 'IHV?', 'IFI?', 'UFI?', 'PAN?', 'SERNO?', 'ANO?', 'STAT?', 'OPE?']
    #for command in command_list:
    #    print(str(command) + ' : ' + str(sc.direct_comm(command)))

    sc.start()

    tui = CursesTui(sc)
    tui.daemon = True
    tui.start()

    #print('Temperature: ' + str(sputter.read_temperature_energy_module()))
    #print('Sputter current: ' + str(sputter.read_sputter_current()))
    #print('Temperature: ' + str(sputter.read_temperature_energy_module()))
    #print('Filament voltage: ' + str(sc.read_filament_voltage()))
    #print('Filament current: ' + str(sc.read_filament_current()))
    #print('Emission current: ' + str(sc.read_emission_current()) + 'A')
    #print('Anode voltage: ' + str(sc.read_anode_voltage()))
    #print('Anode power: ' + str(sc.read_anode_power()) + 'W')

    #sputter.update_status()
    #print('Enable:')
    #print(sputter.remote_enable(local=False))
    #print('Status:')
    #print(sputter.status)
