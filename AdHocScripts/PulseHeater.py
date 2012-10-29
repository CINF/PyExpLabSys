import sys
sys.path.append('../')
import HeaterClass
import agilent_34410A as agilent
import time
import RTD_Calculator
import threading

class CurrentReader(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.heater = Heater
        self.data = []

    def run(self):
        while not quit:
            (I1,I2) = Heater.ReadActualCurrent()
            clock = str(time.time() - init_time)
            self.data.append(clock + " " + str(I1) + " " + clock + " " + str(I2))
            time.sleep(0.25)

class VoltageReader(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.data = []

    def run(self):
        global output
        while not quit:
            self.data.append(str(time.time() - init_time) + " " + str(output))
            time.sleep(0.25)


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

T = TemperatureClass(20) #.... ok not quit the correct thing to do...
T.start()

Heater = HeaterClass.CPXHeater(2)

time.sleep(0.25)

C = CurrentReader()
V = VoltageReader()
C.start()
V.start()
time.sleep(2)


Voltage = 10
Heater.SetVoltage(Voltage)

Heater.OutputStatus(True)
output = str(Voltage)
time.sleep(2)
Heater.OutputStatus(False)
output = "0"
Heater.SetVoltage(0)
time.sleep(5)

quit = True

out = "TempTime Temp VoltageTime Voltage Current1Time Current1 Current2Time Current2" + "\n"
for i in range(0,len(T.data)):
    if i>(len(C.data)-1):
        C.data.append("  ")
    if i>(len(V.data)-1):
        V.data.append("  ")

    out = out + T.data[i] + " " + V.data[i] + " " + C.data[i] + "\n"

f = open('datafile.txt','w')
f.write(out)
f.close()



print("Data file written successfully")
