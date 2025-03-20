"""Driver class for XGS600 gauge controll"""
import time
import serial


class LinkamDriver():
    """Driver for XGS600 gauge controller"""
    def __init__(self, port='/dev/ttyS0', timeout=2.0):
        self.serial = serial.Serial(port)
        self.serial.baudrate = 19200
        self.timeout = timeout

    def comm(self, command):
        """Implements basic communication"""
        # Write command
        self.serial.read(self.serial.inWaiting())  # Clear waiting characters
        comm = command + "\r"
        self.serial.write(comm.encode('ascii'))
        time.sleep(0.1)
        number_of_bytes = self.serial.inWaiting()
        reply = self.serial.read(number_of_bytes)
        # reply = self.serial.readline()
        return reply

    def set_rate(self, rate: float):
        """
        Set the temperature ramp in C/min
        """
        if 0.01 < rate < 150:
            cmd = 'R1' + str(int(rate * 100)) + 'CR'
            self.comm(cmd)
        return

    def set_setpoint(self, setpoint: float):
        """
        Set the setpoint in C. N2 pump is so far not implemented
        only setpoint above room temperature will work.
        """
        if setpoint < 999:  # TODO - Check actual max
            cmd = 'L1' + str(int(setpoint * 10)) + 'CR'
            self.comm(cmd)
        return setpoint

    def start_ramp(self):
        self.comm('S')

    def stop_ramp(self):
        self.comm('E')

    def read_temperature(self):
        t_raw = self.comm('TCR')
        t_hex = t_raw[6:10]
        temperature = int(t_hex, 16)/10
        return temperature


if __name__ == '__main__':
    L = LinkamDriver()
    print(L.read_temperature())
    L.set_setpoint(50)
    L.start_ramp()
    for i in range(0, 60):
        time.sleep(1)
        print(L.read_temperature())
    L.stop_ramp()
    for i in range(0, 20):
        time.sleep(2)
        print(L.read_temperature())
