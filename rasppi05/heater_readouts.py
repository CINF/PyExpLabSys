import sys
import time
sys.path.append('../')
import agilent_34972A as multiplexer
import agilent_34410A as agilent
import CPX400DP as CPX
import RTD_Calculator
import cv
import scipy
import scipy.ndimage
import socket

def ReadTCTemperature():
    HOST, PORT = "rasppi12", 9999
    data = "tempNG"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(data + "\n", (HOST, PORT))
    received = sock.recv(1024)
    temp = float(received)
    return(temp)

def snapshot(name):
    c = cv.CaptureFromCAM(0)
    cv.SetCaptureProperty(c,cv.CV_CAP_PROP_FRAME_WIDTH,320)
    cv.SetCaptureProperty(c,cv.CV_CAP_PROP_FRAME_HEIGHT,240)

    error = True
    while error:
        error = False
        f = cv.QueryFrame(c)
        cv.SaveImage(name + '.png',f)
        img = scipy.misc.imread(name + '.png')
        for i in range(0,img.shape[0],4):
            for j in range(0,img.shape[1],10):
                if ((img[i,j,0] - 10) > img[i,j,1]):
                    error = True
    return(True)

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
    for i in range(1,4):
        heater_drivers[i].SetVoltage(value)
        if i == 1:
            heater_drivers[i].SetVoltage(value*1.2)
        if i == 3:
            heater_drivers[i].SetVoltage(value*0.85)
        heater_drivers[i].OutputStatus(enable)
    time.sleep(0.2)

def read_electrical_status():
    return_string = ""
    res = dmm.read()
    heaters = update_heater_iv()
    t = {}

    return_string += "Time: " + str(time.time() - t_zero)           + "\t"
    return_string += "PS_Voltage: " + str(Vpulse)                   + "\t"
    return_string += "RTD_value:  " + str(res)                      + "\t"
    return_string += "RTD_temp:   " + str(rtd.FindTemperature(res)) + "\t"
    return_string += "TC_temp:    " + str(ReadTCTemperature())      + "\t"

    for channel in [1,2,3]:
        I = heaters['I'][channel]
        V = heaters['V'][channel]
        if I>0:
            R = V/I
        else:
            R = 99999999
        T = heater_rtd[channel].FindTemperature(R)
        return_string += "I" + str(channel) + ": " + str(I) + "\t"
        return_string += "V" + str(channel) + ": " + str(V) + "\t"
        return_string += "R" + str(channel) + ": " + str(R) + "\t"
        return_string += "T" + str(channel) + ": " + str(T) + "\t"

    return_string += "\n"
    return(return_string)


t_zero = time.time()
data_file = ""

mul = multiplexer.Agilent34972ADriver()
dmm = agilent.Agilent34410ADriver()
#dmm.select_measurement_function('FRESISTANCE')
dmm.select_measurement_function('RESISTANCE')
heater_drivers = {}
heater_drivers[1] = CPX.CPX400DPDriver(1,1)
heater_drivers[2] = CPX.CPX400DPDriver(1,0)
heater_drivers[3] = CPX.CPX400DPDriver(2,0)

data_file += "RTD: " + str(dmm.read()) + "\n"

print str(dmm.read())

Vpulse = 0.15
data_file += "Probe voltage: " + str(Vpulse) + "\n"

update_heater_output(Vpulse,True)
print Vpulse

start_temp = ReadTCTemperature()

heaters = update_heater_iv()
rtd = RTD_Calculator.RTD_Calculator(start_temp,dmm.read(),material='Mo')
heater_rtd = {}

for channel in [1,2,3]:
    I = heaters['I'][channel]
    V = heaters['V'][channel]
    R = V/I
    status_string = "Heater {}. Current: {:.4f}mA, Voltage: {:.4f}V, Resistance: {:.4f}\n".format(channel, I*1000,V,R)
    data_file += status_string
    heater_rtd[channel] = RTD_Calculator.RTD_Calculator(start_temp,R,material='Mo')

time.sleep(2)

for i in range(0,50):
    data_file += read_electrical_status()

filename = str(time.time() - t_zero)
snapshot(filename)

for Vpulse in range(1,40,2):
    #Vpulse = 1
    update_heater_output(Vpulse,True)
    print Vpulse

    time.sleep(0.1)

    for i in range(0,50):
        time.sleep(0.1)
        data_file += read_electrical_status()
    filename = str(time.time() - t_zero)
    snapshot(filename)
    for i in range(0,5):
        time.sleep(0.1)
        data_file += read_electrical_status()
    f = open('datafile.txt','w')
    f.write(data_file)
    f.close()


Vpulse = 0.15
update_heater_output(Vpulse,True)
print Vpulse

for i in range(0,5):
    time.sleep(1)
    data_file += read_electrical_status()
filename = str(time.time() - t_zero)
snapshot(filename)
for i in range(0,20):
    time.sleep(5)
    data_file += read_electrical_status()
filename = str(time.time() - t_zero)
snapshot(filename)
for i in range(0,60):
    time.sleep(10)
    data_file += read_electrical_status()
filename = str(time.time() - t_zero)
snapshot(filename)

update_heater_output(0,False)
time.sleep(0.1)


time.sleep(1)

f = open('datafile.txt','w')
f.write(data_file)
f.close()

print data_file
