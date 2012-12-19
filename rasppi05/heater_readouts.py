import sys
import time
sys.path.append('../')
import agilent_34972A as multiplexer
import agilent_34410A as agilent
import CPX400DP as CPX
import RTD_Calculator

def update_heater_iv():
    data = mul.read_single_scan()

    heaters = {}
    heaters['I'] = {}
    heaters['V'] = {}
    heaters['rtd'] = {}

    heaters['I'][1] = data[0]
    heaters['I'][2] = data[2]
    heaters['I'][3] = data[4]
    heaters['V'][1] = data[1]
    heaters['V'][2] = data[3]
    heaters['V'][3] = data[5]
    return(heaters)

def update_heater_output(value,enable):
    heater1.SetVoltage(value)
    heater2.SetVoltage(value)
    heater3.SetVoltage(value)
    heater1.OutputStatus(enable)
    heater2.OutputStatus(enable)
    heater3.OutputStatus(enable)
    time.sleep(0.2)

mul = multiplexer.Agilent34972ADriver()
dmm = agilent.Agilent34410ADriver()
dmm.SelectMeasurementFunction('FRESISTANCE')
heater1 = CPX.CPX400DPDriver(1,1)
heater3 = CPX.CPX400DPDriver(1,0)
heater2 = CPX.CPX400DPDriver(2,0)

print "RTD: " + str(dmm.Read())

Vpulse = 0.1
update_heater_output(Vpulse,True)

heaters = update_heater_iv()
rtd = RTD_Calculator.RTD_Calculator(20,dmm.Read())
heater_rtd = {}

for channel in [1,2,3]:
    I = heaters['I'][channel]
    V = heaters['V'][channel]
    R = V/I
    print "Heater {}. Current: {:.4f}mA, Voltage: {:.4f}V, Resistance: {:.4f}".format(channel, I*1000,V,R)
    heater_rtd[channel] = RTD_Calculator.RTD_Calculator(20,R)

time.sleep(2)

update_heater_output(0.5,True)

time.sleep(1)

for i in range(0,5):
    res = dmm.Read()
    heaters = update_heater_iv()
    #print "RTD: {:.4f}, calculated temperature: {:.4f}".format(res,rtd.FindTemperature(res))
    t = {}
    for channel in [1,2,3]:
        I = heaters['I'][channel]
        V = heaters['V'][channel]
        R = V/I
        t[channel] = heater_rtd[channel].FindTemperature(R)
    print "RTD: {:.4f}, Heater 1: {:.4f}, Heater 2: {:.4f}, Heater 3: {:.4f}".format(rtd.FindTemperature(res),t[1], t[2],t[3])

update_heater_output(0,False)

time.sleep(5)

print "RTD: " + str(dmm.Read())
