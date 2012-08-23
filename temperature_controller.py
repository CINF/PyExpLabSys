import CPX400DP as CPX
import agilent_34410A as agilent
import time
import threading
import subprocess
import curses
import RTD_Calculator
import PID
import NetworkComm


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
        screen.refresh()

class NetworkClass(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.network = NetworkComm.NetworkComm()
        self.setpoint = -999
        self.sample_temperature = -999
        self.rtd_temperature = -999
        self.power = -999

    def run(self):
        while not quit:
            outgoing_dict = {'rtd_temperature': str(self.rtd_temperature),'power': '-1'}
            incomming_dict = self.network.network_sync(outgoing_dict)
            self.setpoint = float(incomming_dict['setpoint'])
            self.sample_temperature = float(incomming_dict['sample_temperature'])
            time.sleep(0.5)

class TemperatureClass(threading.Thread):
    def __init__(self,cal_temperature):
        threading.Thread.__init__(self)
        self.AgilentDriver = agilent.Agilent34410ADriver()
        self.AgilentDriver.SelectMeasurementFunction('RESISTANCE')
        self.rtd_value = self.AgilentDriver.Read()
        self.rtd = self.rtd = RTD_Calculator.RTD_Calculator(cal_temperature,self.rtd_value)
        self.temperature = self.rtd.FindTemperature(self.rtd_value)
        
    def run(self):
        global temperature
        while not quit:
            self.rtd_value = self.AgilentDriver.Read()
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
setpoint = -999
tc_temperature = -999

Network = NetworkClass()
Network.start()

CPXdriver  = CPX.CPX400DPDriver(1)

while (tc_temperature<-100):
    tc_temperature = Network.sample_temperature
    time.sleep(0.5)

T = TemperatureClass(tc_temperature)
T.start()
time.sleep(1)

P = PowerCalculatorClass()
P.start()

TellTheWorld("Calibration value: " + str(T.rtd.Rrt) + "ohm at " + str(T.rtd.Trt) + "C",[1,1])

CPXdriver.SetVoltage(0)
CPXdriver.OutputStatus(True)

power = 0
i = 22*50
while not quit:
    try:
        i = i+1
        time.sleep(0.25)
        setpoint = Network.setpoint
        #setpoint = i/50.0

        
        #RIGHT NOW WHENEVER POWER IS REPLACED WIDTH VOLTAGE!!!!!
        CPXdriver.SetVoltage(P.power)
        I = CPXdriver.ReadActualCurrent()
        #U = CPXdriver.ReadActualVoltage()
        U = P.power

        if I<-99999998:
            del CPXdriver
            time.sleep(1)
            CPXdriver  = CPX.CPX400DPDriver(1)
            I = CPXdriver.ReadActualCurrent()
        if I>0:
            TellTheWorld("PS:" + str(U/I) + "                ",[2,5])
        else:
            TellTheWorld("PS: No current         ",[2,5])

        TellTheWorld("Setpoint: " + str(setpoint) + "        ",[2,4])
        Network.rtd_temperature = T.temperature
        TellTheWorld("Temperature: " + str(T.temperature) + "          ",[2,7])      
        TellTheWorld("Actual Current: " + str(I) + "                   ",[2,9])
        TellTheWorld("Actual Voltage: " + str(U) + "                  ",[2,10])
        TellTheWorld("Wanted power: " + str(P.power) + "              ",[2,11])

    except:
        quit = True
        if output == 'curses':
            curses.nocbreak()
            screen.keypad(0)
            curses.echo()
            curses.endwin()
        
        print "Program terminated by user"
        #print str(e)

CPXdriver.OutputStatus(False)


#print driver.ReadSetVoltage()
#print driver.ReadCurrentLimit()
#print driver.ReadSoftwareVersion()
#print driver.ReadCurrentLimit()
#print driver.ReadSetVoltage()
#print driver.OutputStatus(False)
