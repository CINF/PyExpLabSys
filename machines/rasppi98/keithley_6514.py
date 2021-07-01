import time
import serial

class Keithley(object):
    """Basic driver to make voltage readings from Keithley 6514 Electrometer
    Uses a serial RS232 connection"""

    def __init__(self, port, data_set_saver=None, codename=''):
        self.ser = serial.Serial(port=port,
                          baudrate=57600,
                          parity=serial.PARITY_NONE,
                          stopbits=serial.STOPBITS_ONE,
                          bytesize=serial.EIGHTBITS,
                          xonxoff=False,
                          timeout=0.5,
        )
        self.eol = '\r'
        self.data_set_saver = data_set_saver
        if len(codename) == 0 and not data_set_saver is None:
            raise ValueError('Codename can not be empty if using a database saver')
        else:
            self.codename = codename
            self.metadata = {'type': 70,
                             'sem_voltage': 0,
                             'preamp_range': 0,
                             'comment' : input('Enter comment for measurement (measurement name): ')
                             }

    def comm(self, command, expect_response=True):
        """Send a command to the instrument"""
        command += self.eol
        bytes_prior = self.ser.inWaiting()
        if bytes_prior > 0:
            print('Response queue not empty.')
            response = self.ser.read(bytes_prior)
            print(response)
        self.ser.write(command.encode('ascii'))
        if expect_response:
            response = self.ser.readline()
            return response
        
    def read_voltage(self, meas_range=20, database_saver=False, count=100):
        """Set up instrument to measure voltages"""
        if database_saver:
            #self.comment = input('Comment for measurement: ')
            self.data_set_saver.start()
            time.sleep(1)
            self.data_set_saver.add_measurement(self.codename, self.metadata)

        # Initialize instrument
        self.comm('*RST', False) # Reset device
        self.comm('SYST:ZCH ON', False) # Enable ZERO CHECK
        self.comm('VOLT:GUAR OFF', False) # Disable GUARD
        self.comm('FUNC VOLT', False) # Measure VOLTAGE
        self.comm('VOLT:RANG ' + str(meas_range), False) # Set measurement RANGE
        self.comm('SYST:ZCOR ON', False) # Enable ZERO CORRECT
        self.comm('SYST:ZCH OFF', False) # Disable ZERO CHECK

        # Log continuously
        if count == -1:
            counter = -2
        else:
            counter = 0
        t0 = -1
        while counter < count:
            try:
                if count > -1:
                    counter += 1
                ret = self.comm('READ?') # Read new value
                ret = ret.decode().strip().split(',')
                reading, t, status = float(ret[0]), float(ret[1]), float(ret[2])
                if t0 == -1:
                    t0 = t
                t = t - t0
                if database_saver:
                    self.data_set_saver.save_point(self.codename, (t, reading))
                print(reading, t, status)
            except KeyboardInterrupt:
                break
        print('Emptying buffer..')
        time.sleep(1)
        if self.ser.inWaiting() > 0:
            self.ser.readline()
        print('Done')
        if database_saver:
            self.data_set_saver.stop()
                
if __name__ == '__main__':
    from PyExpLabSys.common.database_saver import DataSetSaver
    import credentials2 as cred
    
    port = '/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0'

    data_set_saver = DataSetSaver('measurements_dummy', 'xy_values_dummy', cred.user, cred.passwd)
    
    dmm = Keithley(port, data_set_saver=data_set_saver, codename='keithley_voltage')
    
    time.sleep(1)
    print(dmm.comm('*IDN?'))
    dmm.read_voltage(meas_range=20, database_saver=True, count=-1)

    
