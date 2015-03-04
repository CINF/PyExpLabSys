import serial
import time

class mks_comm():

    def __init__(self, port):
        self.f = serial.Serial(port, 9600, timeout=2)
        time.sleep(0.1)

    def comm(self, command):
        prestring = '@254'
        endstring = ';FF'
        self.f.write(prestring + command + endstring)
        time.sleep(0.3)
        return_string = self.f.read(self.f.inWaiting())
        return return_string

    def read_pressure(self):
        """ Read the pressure from the device """
        command = 'PR1?'
        error = 1
        while (error > 0) and (error < 10):
            signal = self.comm(command)
            signal = signal[7:-3]
            try:
                signal = float(signal)
                error = 0
            except ValueError:
                error = error + 1
                signal = -1
        return signal

    def set_comm_speed(self, speed):
        """ Change the baud rate """
        command = 'BR!' + str(speed)
        signal = self.comm(command)
        return(signal)

    def change_unit(self, unit): #STRING: TORR, PASCAL, MBAR
        """ Change the unit of the return value """
        command = 'U!' + unit
        signal = self.comm(command)
        return(signal)

    def read_serial(self):
        """ Read the serial number of the device """
        command = 'SN?'
        signal = self.comm(command)
        signal = signal[7:-3]
        return(signal)

if __name__ == '__main__':
    mks = mks_comm('/dev/ttyUSB1')
    #print mks.set_comm_speed(9600)
    print mks.change_unit('MBAR')
    print "Pressure: " + str(mks.read_pressure())
    print 'Serial: ' + str(mks.read_serial())
