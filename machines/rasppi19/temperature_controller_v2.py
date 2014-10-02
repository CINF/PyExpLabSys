# -*- coding: utf-8 -*-
"""
Spyder Editor

Author:
Anders Nierhoff

changed:
2014-10-01
"""


import time
import threading
#import subprocess
import curses
import socket
import serial 
from datetime import datetime
import MySQLdb

import sys
sys.path.append('../../')
import PyExpLabSys.drivers.cpx400dp as CPX


#output = 'print'
#output = 'curses'

class PID():
    """Implementation of a PID routine

    Iterates over all devices in /dev/input/event?? and looks for one that has
    'Barcode Reader' in its description.

    Returns:
        str: The Barcode Scanner device path
    """
    
    def __init__(self, case=None):
        """The input parameter case is used to simplify that several system is sharing the software, each with it own parametors."""
        if case == None:
            self.gain = {'Kp':0.15,'Ki':0.0025,'Kd':0.0,'Pmax':54.0, 'Pmin':0.0}
            pass
        elif case == 'stm312 hpc':
            self.gain = {'Kp':0.15, 'Ki':0.0025, 'Kd':0.0, 'Pmax':54.0, 'Pmin':0.0}
            
        """ Provid a starting setpoit to ensure that the PID does not apply any power before an actual setpoit is set."""
        self.setpoint = -9999
        self.Kp = self.gain['Kp']
        self.Ki = self.gain['Ki']
        self.Kd = self.gain['Kd']
        self.Pmax = self.gain['Pmax']
        self.Pmin = self.gain['Pmin']
        
    def initialize(self,):
        """ Initialize delta t variables. """
        self.currtm = time.time()
        self.prevtm = self.currtm

        self.prev_err = 0

        # term result variables
        self.Cp = 0
        self.Ci = 0
        self.Cd = 0
        self.P = 0

    def reset_integrated_error(self):
        """ Reset the I value, integrated error. """
        self.Ci = 0

    def update_setpoint(self, setpoint):
        """ Update the setpoint."""
        self.setpoint = setpoint
        return setpoint

    def get_new_Power(self,T):
        """ Get new power for system, P_i+1 

        :param T: Actual temperature
        :type T: float
        :returns: best guess of need power
        :rtype: float
        """
        error = self.setpoint - T
        self.currtm = time.time()               # get t
        dt = self.currtm - self.prevtm          # get delta t
        de = error - self.prev_err  
        
        """ Calculate proportional gain. """
        self.Cp = error
        
        """ Calculate integral gain, including limits """
        if self.prev_P > self.Pmax and error > 0:
            pass
        elif self.prev_P < self.Pmin and error < 0:
            pass
        else:
            self.Ci += error * dt
        
        """ Calculate derivative gain. """
        if dt > 0:                              # no div by zero
            self.Cd = de/dt 
        else:
            self.Cd = 0
            
        """ Adjust times, and error for next iteration. """
        self.prevtm = self.currtm               # save t for next pass
        self.prev_err = error                   # save t-1 error
        
        """ Calculate Output. """
        P = self.Kp * self.Cp + self.Ki * self.Ci + self.Kd * self.Cd
        self.prev_P = P
        
        """ Check if output is valid. """
        if P > self.Pmax:
            P = self.Pmax
        if P < 0:
            P = 0 
        return P

class CursesTui(threading.Thread):
    def __init__(self,powercontrolclass):
        threading.Thread.__init__(self)
        self.pcc = powercontrolclass
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
        
    def run(self,):
        while self.running:
            self.screen.addstr(3, 2, 'Power Supply for HPC stm312, ID: ')# + str(self.ps.status('ID'))
            if self.pcc.status['Output']:
                self.screen.addstr(4, 2, 'Power Output: '+str(self.pcc.status['Output']))# + str(self.ps.status('ID'))
                self.screen.addstr(5, 2, 'Control mode: '+str(self.pcc.status['Mode']))
            try:
                self.screen.addstr(6, 2, "Current: {0:.1f}A".format(self.pcc.status['Current']))
                self.screen.addstr(7, 2, "Voltage: {0:.1f}V".format(self.pcc.status['Voltage']))
                self.screen.addstr(8, 2, "Power: {0:.1f}W".format(self.pcc.status['Actual Power']))
                self.screen.addstr(9, 2, "Resistance: {0:.1f}Ohm".format(self.pcc.status['Resistance']))
            except:
                pass
            if self.pcc.status['error'] != None:
                self.screen.addstr(18,2, 'Latest error message: ' + str(self.pcc.status['error']) + ' at time: ' + str(self.pcc.status['error time']))
            self.screen.addstr(19,2,"Runtime: {0:.0f}s".format(time.time() - self.time))
            self.screen.addstr(21,2,"q: quit program, ")
            self.screen.addstr(22,2,"t: PID temperature control, i, fixed current, v: fixed voltage")
            self.screen.addstr(24,2, ' Latest key: ' + str(self.last_key))
            n = self.screen.getch()
            if n == ord("q"):
                self.pcc.running = False
                self.running = False
                self.last_key = chr(n)
            elif n == ord('t'):
                self.pcc.status['Mode'] = 'Temperature Control'
                self.last_key = chr(n)
            elif n == ord('i'):
                self.pcc.status['Mode'] = 'Current Control'
                self.last_key = chr(n)
            elif n == ord('v'):
                self.pcc.status['Mode'] = 'Voltage Control'
                self.last_key = chr(n)
        time.sleep(5)
        self.stop()
        #print EXCEPTION

    def stop(self):
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()

def sqlTime():
    sqltime = datetime.now().isoformat(' ')[0:19]
    return(sqltime)


def sqlInsert(query):
    try:
        cnxn = MySQLdb.connect(host="servcinf",user="stm312",passwd="stm312",db="cinfdata")
        cursor = cnxn.cursor()
    except:
	print "Unable to connect to database"
	return()
    try:
        cursor.execute(query)
        cnxn.commit()
    except:
        print "SQL-error, query written below:"
        print query
    cnxn.close()


"""if output == 'curses':
    screen = curses.initscr()
    curses.noecho()
    curses.cbreak()
    curses.curs_set(False)
    screen.keypad(1)
"""


"""
def TellTheWorld(message,pos=[0,0]):
    if output == 'print':
        print(message)
    if output == 'curses':
        screen.addstr(pos[1], pos[0], message)
"""

def network_comm(host, port, string):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(string + "\n", (host, port))
    received = sock.recv(1024)
    return received

def read_hp_temp():
    received = network_comm('rasppi19',9990, 'read_hp_temp')
    temp = float(received)
    return(temp)

def read_setpoint():
    received = network_comm('rasppi19',9990, 'read_setpoint')
    temp = float(received)
    return(temp)

class TemperatureClass(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.temperature = -999
        self.running = True
        
    def run(self):
        while self.running:
            self.temperature = float(read_hp_temp())
            temperature = self.temperature
            time.sleep(0.25)
    def stop(self,):
        self.running = False
        pass

"""
class PowerCalculatorClass(threading.Thread):
    def __init__(self, temp_class):
        threading.Thread.__init__(self)
        self.power = 0
        self.setpoint = -200
        self.pid = PID.PID()
        self.pid.Kp = 0.035
        self.pid.Ki = 0.00022
        self.pid.Kd = 0
        self.pid.Pmax = 8
        self.pid.UpdateSetpoint(self.setpoint)
        self.temp_class = temp_class
        self.running = True
        
    def run(self):
        #global power
        while self.running:
            self.power = self.pid.WantedPower(self.temp_class.temperature)
            self.pid.UpdateSetpoint(self.setpoint)SetVoltage
            time.sleep(0.25)
        self.pid.UpdateSetpoint(-200)
    def stop(self,):
        self.running = False
        pass
"""

class PowerControlClass(threading.Thread):
    
    def __init__(self,):
        threading.Thread.__init__(self)
        #self.PowerCalculatorClass = PID_class
        self.running = True
        self.status = {}
        self.status['Mode'] = 'Temperature Control' #, 'Power Control'
        self.status['error'] = None
        self.init_PID_class()
        #self.init_temp_class()
        self.init_heater_class()
    
    def init_temp_class(self,temp_class):
        self.temp_class = temp_class
        
    def init_PID_class(self,):
        self.power = 0.0
        self.setpoint = -200.0
        self.pid = PID()
        self.pid.Kp = 0.035
        self.pid.Ki = 0.00022
        self.pid.Kd = 0.0
        self.pid.Pmax = 8.0
        self.pid.update_setpoint(self.setpoint)
        self.status['Wanted power'] = self.power
        self.status['Setpoint'] = self.setpoint
        
    def init_heater_class(self,):
        for i in range(0,10):
            heater = CPX.CPX400DPDriver(1,usbchannel=i)
            if not heater.debug:
                break
        self.heater = heater
        
    def init_resistance(self,):
        self.heater.set_voltage(2)
        self.heater.output_status(on=True)
        time.sleep(1)
        I_calib = self.heater.read_actual_current()
        self.heater.output_status(on=False)
        self.R_calib = 2.0/I_calib
        
    def OutputOn(self,):
        self.status['Output'] = True
        self.heater.output_status(on=True)
        
    def OutputOff(self,):
        self.status['Output'] = False
        self.heater.output_status(on=False)
        
    def update_output(self,):
        self.status['Current'] = heater.read_actual_current()
        self.status['Voltage'] = heater.read_actual_voltage()
        self.status['Actual Power'] = self.status['Current']* self.status['Voltage']
        self.status['Resistance'] = self.status['Voltage'] / self.status['Current']
        pass
    
    def run(self,):
        self.heater.set_voltage(0)
        self.OutputOn()
        while self.running:
            self.status['Setpoint'] = read_setpoint()
            if self.status['Mode'] == 'Temperature Control':
                self.pid.update_setpoint(self.status['Setpoint'])
                self.status['Wanted power'] = self.pid.get_new_Power(self.temp_class.temperature)
                self.status['Wanted Voltage'] = ( self.status['Wanted power']* self.status['Resistance'] )**0.5
            elif self.status['Mode'] == 'Power Control':
                if self.status['Setpoint'] > 0 or self.status['Setpoint'] < 100:
                    self.status['Wanted power'] = self.status['Setpoint']
                    self.status['Wanted Voltage'] = ( self.status['Wanted power']* self.status['Resistance'] )**0.5
            elif self.status['Mode'] == 'Current Control':
                if self.status['Setpoint'] > 0 or self.status['Setpoint'] < 10:
                    self.status['Wanted Voltage'] = self.status['Resistance']* self.status['Setpoint']
            elif self.status['Mode'] == 'Voltage Control':
                if self.status['Setpoint'] > 0 or self.status['Setpoint'] < 10:
                    self.status['Wanted Voltage'] = self.status['Setpoint']
            time.sleep(0.25)            
            try:
                self.heater.set_voltage(self.status['Wanted Voltage'])
                if self.heater.debug:
                    raise serial.serialutil.SerialException
            except serial.serialutil.SerialException:
                self.init_heater()
            self.update_output()
        self.pid.update_setpoint(-200)
        self.OutputOff()
        self.stop()
        
    def stop(self,):
        try:
            self.temp_class.stop()
        except:
            pass
    
"""
quit = False

for i in range(0,10):
    heater = CPX.CPX400DPDriver(1,usbchannel=i)
    if not heater.debug:
        break

T = TemperatureClass()
T.start()
time.sleep(1)


# Calibrate resistance of the heater
heater.SetVoltage(2)
heater.OutputStatus(True)
time.sleep(1)
I_calib = heater.ReadActualCurrent()
heater.OutputStatus(False)
R_calib = 2.0/I_calib

time.sleep(1)

P = PowerCalculatorClass(T)
P.start()

TellTheWorld("Calibration value, R: {0:.3f} ohm at {1:.1f}C".format(R_calib,T.temperature),[2,2])

heater.SetVoltage(0)
heater.OutputStatus(True)

start_time = time.time()
usb_reset = 0
trigger = 0
while not quit:
    try:
        time.sleep(0.25)
        P.setpoint = read_setpoint()

        try:
            heater.SetVoltage(P.power) #Power means voltage in this case...
            I = heater.ReadActualCurrent()
            U = heater.ReadActualVoltage()
            trigger = trigger + 1
            if trigger > 20:
                meas_time = sqlTime()
                sql = "insert into dateplots_stm312 set type=40, time=\"" +  meas_time + "\", value = \"" + str(U) + "\""
                sqlInsert(sql)
                sql = "insert into dateplots_stm312 set type=41, time=\"" +  meas_time + "\", value = \"" + str(I) + "\""
                sqlInsert(sql)
                trigger = 0

            if heater.debug:
                raise serial.serialutil.SerialException
        except serial.serialutil.SerialException:
            time.sleep(0.5)
            usb_reset += 1
            for i in range(0,10):
                heater = CPX.CPX400DPDriver(1,usbchannel=i)
                if not heater.d/home/aufn/.spyder2/.temp.pyebug:
                    break
            #del heater
            #time.sleep(0.1)
            #heater = CPX.CPX400DPDriver(1,usbchannel=0)
            #if heater.debug:
            #    del heater
            #    heater = CPX.CPX400DPDriver(1,usbchannel=1)
            I = heater.ReadActualCurrent()
            U = heater.ReadActualVoltage()

        if I>0.01:
            TellTheWorld("R:  {0:.2f}           ".format(U/I),[2,3])
        else:
            TellTheWorld("R: -                  ",[2,3])


        TellTheWorld("Setpoint:  {0:.2f}".format(P.setpoint),[2,5])
        TellTheWorld("Temperature: {0:.4f}".format(T.temperature),[2,6])      

        TellTheWorld("I: {0:.3f}".format(I),[2,9])
        TellTheWorld("Wanted Voltage: {0:.4f}".format(P.power),[2,10])
        TellTheWorld("Actual Voltage: {0:.4f}".format(U),[2,11])
        TellTheWorld("Actual power: {0:.4f}".format(U*I),[2,12])

        TellTheWorld('Port: ' + str(heater.f.portstr),[2,15])
        TellTheWorld('Run time:  {0:.1f}'.format(time.time() - start_time),[2,16])
        TellTheWorld('USB-resets:  {0:.0f}'.format(usb_reset),[2,17])

        if output == 'curses':
            screen.refresh()
    except KeyboardInterrupt:
        quit = True

        if output == 'curses':
            curses.nocbreak()
            screen.keypad(0)
            curses.echo()
            curses.endwin()
        
        print "Program terminated by user"
        print sys.exc_info()[0]
        print sys.exc_info()[1]
        print sys.exc_info()[2]

heater.SetVoltage(0)
heater.OutputStatus(False)
"""

if __name__ == '__main__':
    print('Program start')
    
    #classes: 
    TempClass = TemperatureClass()
    TempClass.start()
    
    pcc = PowerControlClass()
    pcc.init_temp_class(TempClass)
    pcc.start()

    tui = CursesTui(pcc)
    tui.daemon = True
    tui.start()
    
    print('Program End')
