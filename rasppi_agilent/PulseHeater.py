import sys
sys.path.append('../')
#import HeaterClass
import CPX400DP as CPX
import agilent_34410A as agilent
import time
import RTD_Calculator
import threading
import socket
import os

from subprocess import call

class CurrentReader(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.heater = Heater
        self.data = []

    def reset(self):
        self.data = []


    def run(self):
        while not quit:
            I = Heater.ReadActualCurrent()
            clock = str(time.time() - init_time)
            self.data.append(clock + " " + str(I))
            time.sleep(0.2)

class VoltageReader(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.data = []

    def reset(self):
        self.data = []


    def run(self):
        global output
        while not quit:
            self.data.append(str(time.time() - init_time) + " " + str(output))
            time.sleep(0.1)


class TemperatureClass(threading.Thread):
    def __init__(self,cal_temperature):
        threading.Thread.__init__(self)
        self.AgilentDriver = agilent.Agilent34410ADriver()
        self.AgilentDriver.SelectMeasurementFunction('FRESISTANCE')
        #self.AgilentDriver.SelectMeasurementFunction('RESISTANCE')
        self.rtd_value = self.AgilentDriver.Read()
        self.rtd = self.rtd = RTD_Calculator.RTD_Calculator(cal_temperature,self.rtd_value)
        self.temperature = self.rtd.FindTemperature(self.rtd_value)
        self.data = []

    def reset(self):
        self.data = []

    def run(self):
        global temperature
        global out
        while not quit:
            self.rtd_value = self.AgilentDriver.Read()
            self.temperature = self.rtd.FindTemperature(self.rtd_value)
            temperature = self.temperature
            self.data.append(str(time.time() - init_time) + " " + str(temperature))
            time.sleep(0.01)

output = "0"
init_time = time.time()
quit = False

T = TemperatureClass(70) #.... ok not quit the correct thing to do...
T.start()

#Heater = HeaterClass.CPXHeater(2)
Heater = CPX.CPX400DPDriver(1)

time.sleep(0.25)

C = CurrentReader()
V = VoltageReader()
C.start()
V.start()
time.sleep(2)

#Voltages = [5,10,15,20,25,30,32,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59]
Voltages = [60]

for Voltage in Voltages:

    C.reset()
    V.reset()
    T.reset()

    Heater.SetVoltage(Voltage)
    time.sleep(10)

    Heater.OutputStatus(True)
    output = str(Voltage)
    time.sleep(120)
    Heater.OutputStatus(False)
    output = "0"
    Heater.SetVoltage(0)
    time.sleep(5)
    
    out = "TempTime Temp VoltageTime Voltage Current1Time Current1 Current2Time Current2" + "\n"
    for i in range(0,len(T.data)):
        if i>(len(C.data)-1):
            C.data.append("    ")
        if i>(len(V.data)-1):
            V.data.append("  ")
        out = out + T.data[i] + " " + V.data[i] + " " + C.data[i] + "\n"

    f = open('datafile_' + str(Voltage)  + '.txt','w')
    f.write(out)
    f.close()

    """
    HOST, PORT = "130.225.87.213", 9999 #rasppi04                                                                                    
    data = "picture"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(data + "\n", (HOST, PORT))
    received = sock.recv(1024)
    call(["wget", received])

    os.rename("tmp.jpg","picture_" + str(Voltage) + ".jpg")
    """

    print("Data file written successfully")

quit = True
