import CPX400DP as CPX
import agilent_34410A as agilent
import time
import subprocess
import random
import curses
import RTD_Calculator
import PID

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

def VBoxWrite(name,value):
    shell_string = '/usr/bin/VBoxControl -nologo guestproperty set '
    if type(value) is str:
        shell_string += name + ' ' + value
    else:
        shell_string += name + ' ' + str(value)
    subprocess.call(shell_string,shell=True)

def VBoxRead(name):
    shell_string = '/usr/bin/VBoxControl -nologo guestproperty get '
    shell_string += name
    p = subprocess.Popen(shell_string,shell=True, stdout=subprocess.PIPE)
    out, err = p.communicate()
    read_val = out.strip()
    read_val = float(read_val[7:].replace(",",".",1))
    return(read_val)


CPXdriver  = CPX.CPX400DPDriver(1)
AgilentDriver = agilent.Agilent34410ADriver()

AgilentDriver.SelectMeasurementFunction('RESISTANCE')

cal_resistance = AgilentDriver.Read()
tc_temperature = VBoxRead('tc_temperature')

TellTheWorld("Calibration value: " + str(cal_resistance) + "ohm at " + str(tc_temperature) + "C",[1,1])

rtd = RTD_Calculator.RTD_Calculator(tc_temperature,cal_resistance)

#print AgilentDriver.ReadSoftwareVersion()
#AgilentDriver.SelectMeasurementFunction('RESISTANCE')

CPXdriver.SetVoltage(0)
CPXdriver.OutputStatus(True)
pid = PID.PID()
pid.UpdateSetpoint(0)

quit = False
power = 0
i = 22*50
while not quit:
    try:
        i = i+1
        time.sleep(0.25)
        #setpoint = VBoxRead('setpoint')
        setpoint = i/50.0

        pid.UpdateSetpoint(setpoint)
        
        #RIGHT NOW WHENEVER POWER IS REPLACED WIDTH VOLTAGE!!!!!
        CPXdriver.SetVoltage(power)
        I = CPXdriver.ReadActualCurrent()
        U = CPXdriver.ReadActualVoltage()

        if I<-99999998:
            del CPXdriver
            time.sleep(1)
            CPXdriver  = CPX.CPX400DPDriver(1)
        if I>0:
            TellTheWorld("PS:" + str(U/I) + "         ",[2,5])
        else:
            TellTheWorld("PS: No current         ",[2,5])

        rtd_val = AgilentDriver.Read()
        TellTheWorld("Setpoint: " + str(setpoint) + "  ",[2,4])
        TellTheWorld("Agilent: " + str(rtd_val) + "    ",[2,6])
        RTD_Temp = rtd.FindTemperature(rtd_val)
        VBoxWrite("RTD_Temp",RTD_Temp)
        power = pid.WantedPower(RTD_Temp)
        TellTheWorld("Temperature: " + str(RTD_Temp) + "       ",[2,7])
        
        TellTheWorld("Actual Current: " + str(I) + "           ",[2,9])
        TellTheWorld("Actual Voltage: " + str(U) + "          ",[2,10])
        TellTheWorld("Wanted power: " + str(power) + "         ",[2,11])

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

#VBoxWrite('setpoint','2')

#print driver.ReadSetVoltage()
#print driver.ReadCurrentLimit()
#print driver.ReadSoftwareVersion()
#print driver.ReadCurrentLimit()
#print driver.ReadSetVoltage()
#print driver.OutputStatus(False)
