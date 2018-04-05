""" Driver for IL800 deposition controller """
import serial

class IL800(object):
    """ Driver for IL800 depostition controller """
    def __init__(self, port):
        self.serial = serial.Serial(port, 9600, timeout=3, xonxoff=False, rtscts=True)

    def comm(self, command):
        """ Communicate with instrument """
        self.serial.write(command + '\r')
        status = self.serial.read(2)
        if status[0] == '0': #Everything ok
            ret_value = ' '
            while not ret_value[-1] == '\r':
                ret_value += self.serial.read()
        return ret_value[1:-1]

    def rate(self):
        """Return the deposition rate in nm/s"""
        rate = self.comm('CHKRATE')
        return float(rate)

    def thickness(self):
        """ Return the currently measured thickness in nm """
        thickness = self.comm('CHKTHICKNESS')
        return float(thickness)

    def frequency(self):
        """ Return the qrystal frequency in Hz """
        thickness = self.comm('CHKXTAL')
        return float(thickness)

if __name__ == '__main__':
    IL800_UNIT = IL800('/dev/ttyUSB1')

    print(IL800_UNIT.rate())
    print(IL800_UNIT.thickness())
    print(IL800_UNIT.frequency())
