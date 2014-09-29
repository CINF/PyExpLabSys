import time
import threading
#import subprocess
import curses
import socket
import serial 
from datetime import datetime
import MySQLdb

import sys
sys.path.append('../')
import CPX400DP as CPX
import PID

#output = 'print'
output = 'curses'

class CursesTui(threading.Thread):
    def __init__(self,powersupply):
        treading.Tread.__init__(self)
        self.ps = powersupply
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
            if self.ps.status['eroor'] != None:
                self.screen.addstr(18,2, 'Latest error message: ' + str(self.ps.status['error']) + ' at time: ' + str(self.ps.status['error time']))
            self.screen.addstr(19,2,"Runtime: {0:.0f}s".format(time.time() - self.time))
            self.screen.addstr(21,2,"q: quit program, ")
            self.screen.addstr(24,2, ' Latest key: ' + str(self.last_key))
            n = self.screen.getch()
            if n == ord("q"):
                self.ps.running = False
                self.running = False
                self.last_key = chr(n)
            elif n == ord(''):
                self.ps.goto_manual = True
                self.last_key = chr(n)
        time.sleep(5)
        self.stop()
        print EXCEPTION

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


if output == 'curses':
    screen = curses.initscr()
    curses.noecho()
    curses.cbreak()
    curses.curs_set(False)
    screen.keypad(1)

def TellTheWorld(message,pos=[0,0]):
    if output == 'print':
        print(message)
    if output == 'curses':
        screen.addstr(pos[1], pos[0], message)

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
        
    def run(self):
        while not quit:
            self.temperature = float(read_hp_temp())
            temperature = self.temperature
            time.sleep(0.25)


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
        
    def run(self):
        global power
        while not quit:
            self.power = self.pid.WantedPower(self.temp_class.temperature)
            self.pid.UpdateSetpoint(self.setpoint)
            time.sleep(0.25)


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
                if not heater.debug:
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
if __name__ == '__main__':
    """
    ps = powersupply()
    ps.start()

    tui = CursesTui(ps)
    tui.daemon = True
    tui.start()
    """
    pass
