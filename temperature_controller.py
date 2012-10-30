#import CPX400DP as CPX
import HeaterClass
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
        #screen.refresh()

def ReadTCTemperature():
    HOST, PORT = "rasppi04", 9999 #robertj                                                          data = "tempNG"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(data + "\n", (HOST, PORT))
    received = sock.recv(1024)
    temp = float(received)
    return(temp)


class NetworkClass(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.network = NetworkComm.NetworkComm()
        self.setpoint = -999
        self.sample_temperature = -999
        self.rtd_temperature = -999
        self.power = -999
        self.last_sync = time.time()
        self.network_errors = 0

    def run(self):
        while not quit:
            outgoing_dict = {'rtd_temperature': str(self.rtd_temperature),'power': '-1'}

            incomming_dict = self.network.network_sync(outgoing_dict)
            if incomming_dict['setpoint'] <> 'error':
                self.setpoint = float(incomming_dict['setpoint'])
                self.sample_temperature = float(incomming_dict['sample_temperature'])
                self.last_sync = time.time()
                time.sleep(1)
            else:
                self.network_errors += 1

class TemperatureClass(threading.Thread):
    def __init__(self,cal_temperature):
        threading.Thread.__init__(self)
        self.AgilentDriver = agilent.Agilent34410ADriver()
        self.AgilentDriver.SelectMeasurementFunction('FRESISTANCE')
        #self.AgilentDriver.SelectMeasurementFunction('RESISTANCE')
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
tc_temperature = ReadTCTemperatur()

#CPXdriver  = CPX.CPX400DPDriver(1)
Heater = HeaterClass.CPXHeater(2)

Network = NetworkClass()
Network.start()
while (tc_temperature<-100):
    tc_temperature = Network.sample_temperature
    time.sleep(0.5)

T = TemperatureClass(tc_temperature)
T.start()
time.sleep(1)

P = PowerCalculatorClass()
P.start()

TellTheWorld("Calibration value: " + str(T.rtd.Rrt) + "ohm at " + str(T.rtd.Trt) + "C",[1,1])

#CPXdriver.SetVoltage(0)
#CPXdriver.OutputStatus(True)
Heater.SetVoltage(0)
Heater.OutputStatus(True)

power = 0

while not quit:
    try:
        time.sleep(0.25)
        setpoint = Network.setpoint

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
        if I1>0:
            TellTheWorld("Resistance1, PS:  {0:.5f}    ".format(U/I1),[2,5])
        else:
            TellTheWorld("Pesistance1, PS: -   ",[2,5])
        if I2>0:
            TellTheWorld("Resistance2, PS:  {0:.5f}    ".format(U/I2),[35,5])
        else:
            TellTheWorld("Resistance2, PS: -   ",[35,5])


        TellTheWorld("Setpoint: " + str(setpoint) + "     ",[2,4])
        Network.rtd_temperature = T.temperature
        TellTheWorld("Temperature: {0:.4f}".format(T.temperature),[2,7])      
        TellTheWorld("RTD resistance: {0:.5f}".format(T.rtd_value),[2,8])

        TellTheWorld("Actual Current1: {0:.4f}".format(I1),[2,9])
        TellTheWorld("Actual Current2: {0:.4f}".format(I2),[35,9])
        TellTheWorld("Actual Voltage: {0:.4f}".format(U),[2,10])
        TellTheWorld("Wanted power: {0:.4f}".format(P.power),[2,11])
        time_since_sync = time.time() - Network.last_sync

        TellTheWorld("Sync time: {0:.2f}".format(time_since_sync),[2,12])
        TellTheWorld("Network resets: " + str(Network.network_errors) + "          ",[2,13])
        if output == 'curses':
            screen.refresh()


    except:
        quit = True
        del Network

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
