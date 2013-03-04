#import CPX400DP as CPX
import HeaterClass
import agilent_34410A as agilent
import time
import threading
import subprocess
import curses
import RTD_Calculator
import PID
import socket

#output = 'print'
output = 'curses'

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
        #screen.refresh()

def ReadTCTemperature():
    HOST, PORT = "rasppi12", 9999
    data = "tempNG"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(data + "\n", (HOST, PORT))
    received = sock.recv(1024)
    temp = float(received)
    return(temp)

def ReadSetpoint():
    HOST, PORT = "rasppi05", 9999
    data = "read_setpoint"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(data + "\n", (HOST, PORT))
    received = sock.recv(1024)
    temp = float(received)
    return(temp)

def set_rtdval(value):
    HOST, PORT = "rasppi05", 9999
    data = "set_rtdval " + str(value)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(data + "\n", (HOST, PORT))
    received = sock.recv(1024)
    return_val = False
    if received == "ok":
        return_val = True
    return return_val


class TemperatureClass(threading.Thread):
    def __init__(self,cal_temperature):
        threading.Thread.__init__(self)
        self.AgilentDriver = agilent.Agilent34410ADriver()
        self.AgilentDriver.select_measurement_function('FRESISTANCE')
        #self.AgilentDriver.select_measurement_function('RESISTANCE')
        self.rtd_value = self.AgilentDriver.read()
        self.rtd = RTD_Calculator.RTD_Calculator(cal_temperature,self.rtd_value)
        self.temperature = self.rtd.FindTemperature(self.rtd_value)
        
    def run(self):
        global temperature
        while not quit:
            self.rtd_value = self.AgilentDriver.read()
            self.temperature = self.rtd.FindTemperature(self.rtd_value)
            temperature = self.temperature
            time.sleep(0.25)


class PowerCalculatorClass(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.power = 0
        self.setpoint = setpoint
        self.pid = PID.PID()
        self.pid.UpdateSetpoint(self.setpoint)
        
    def run(self):
        global power
        while not quit:
            self.power = self.pid.WantedPower(temperature)
            self.setpoint = setpoint
            self.pid.UpdateSetpoint(self.setpoint)
            time.sleep(0.25)


quit = False
setpoint = ReadSetpoint()
tc_temperature = ReadTCTemperature()

#CPXdriver  = CPX.CPX400DPDriver(1)
Heater = HeaterClass.CPXHeater(2)

#Network = NetworkClass()
#Network.start()
#while (tc_temperature<-100):
#    tc_temperature = Network.sample_temperature
#    time.sleep(0.5)

T = TemperatureClass(tc_temperature)
T.start()
time.sleep(1)

# Calibrate resistance of the heaters
Heater.SetVoltage(3)
Heater.OutputStatus(True)
time.sleep(1)
(I1_calib,I2_calib) = Heater.ReadActualCurrent()
Heater.OutputStatus(False)
R1_calib = 3/I1_calib
R2_calib = 3/I2_calib
Heater1_rtd = RTD_Calculator.RTD_Calculator(tc_temperature,R1_calib)
Heater2_rtd = RTD_Calculator.RTD_Calculator(tc_temperature,R2_calib)

time.sleep(1)

P = PowerCalculatorClass()
P.start()

TellTheWorld("Calibration value: {0:.5f} ohm at {1:.1f}C".format(T.rtd.Rrt,T.rtd.Trt),[2,1])
TellTheWorld("Calibration value, I1: {0:.3f} ohm at {1:.1f}C".format(Heater1_rtd.Rrt,T.rtd.Trt),[2,2])
TellTheWorld("Calibration value, I2: {0:.3f} ohm at {1:.1f}C".format(Heater2_rtd.Rrt,T.rtd.Trt),[2,3])

#CPXdriver.SetVoltage(0)
#CPXdriver.OutputStatus(True)
Heater.SetVoltage(0)
Heater.OutputStatus(True)


power = 0

while not quit:
    try:
        time.sleep(0.25)
        setpoint = setpoint = ReadSetpoint()

        #RIGHT NOW WHENEVER POWER IS REPLACED WIDTH VOLTAGE!!!!!
        #CPXdriver.SetVoltage(P.power)
        Heater.SetVoltage(P.power)
        #I = CPXdriver.ReadActualCurrent()
        (I1,I2) = Heater.ReadActualCurrent()
        #U = CPXdriver.ReadActualVoltage()
        U = P.power
        if I1<-99999998 or I2<-99999998:
            #del CPXdriver
            del Heater
            time.sleep(1)
            #CPXdriver  = CPX.CPX400DPDriver(1)
            Heater = HeaterClass(2)
            #I = CPXdriver.ReadActualCurrent()
            (I1,I2) = Heater.ReadActualCurrent()
        if I1>0.01:
            TellTheWorld("Resistance1, PS:  {0:.4f}               ".format(U/I1),[2,5])
            TellTheWorld("Temperature 1: {0:.3f}                  ".format(Heater1_rtd.FindTemperature(U/I1)),[2,6])
        else:
            TellTheWorld("Resistance1, PS: -                      ",[2,5])
            TellTheWorld("Temperature 1: -                        ",[2,6])
        if I2>0.01:
            TellTheWorld("Resistance2, PS:  {0:.4f}               ".format(U/I2),[35,5])
            TellTheWorld("Temperature 2: {0:.3f}                  ".format(Heater1_rtd.FindTemperature(U/I2)),[35,6])
        else:
            TellTheWorld("Resistance2, PS: -                      ",[35,5])
            TellTheWorld("Temperature 2: -                        ",[35,6])


        TellTheWorld("Setpoint: " + str(setpoint) + "     ",[2,8])
        set_rtdval(T.temperature) # Check that the return value is actually true...
        TellTheWorld("Temperature: {0:.4f}".format(T.temperature),[2,9])      
        TellTheWorld("RTD resistance: {0:.5f}".format(T.rtd_value),[2,10])

        TellTheWorld("Actual Current1: {0:.4f}".format(I1),[2,11])
        TellTheWorld("Actual Current2: {0:.4f}".format(I2),[35,11])
        TellTheWorld("Actual Voltage: {0:.4f}".format(U),[2,12])
        TellTheWorld("Wanted power: {0:.4f}".format(P.power),[2,14])
        TellTheWorld("Actual power: {0:.4f}".format(P.power*(I1+I2)),[2,15])
        #time_since_sync = time.time() - Network.last_sync

        #TellTheWorld("Sync time: {0:.2f}".format(time_since_sync),[2,14])
        #TellTheWorld("Network resets: " + str(Network.network_errors) + "          ",[2,16])
        if output == 'curses':
            screen.refresh()
    except:
        quit = True

        if output == 'curses':
            curses.nocbreak()
            screen.keypad(0)
            curses.echo()
            curses.endwin()
        
        print "Program terminated by user"
        #print str(e)

#CPXdriver.OutputStatus(False)
Heater.OutputStatus(False)


#print driver.ReadSetVoltage()
#print driver.ReadCurrentLimit()
#print driver.ReadSoftwareVersion()
#print driver.ReadCurrentLimit()
#print driver.ReadSetVoltage()
#print driver.OutputStatus(False)
