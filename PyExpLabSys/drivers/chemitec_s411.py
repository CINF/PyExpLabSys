import time
import serial
import minimalmodbus

class ChemitecS411(object):
    def __init__(self):
        self.comm = minimalmodbus.Instrument('/dev/ttyUSB0', 18)
        self.comm.serial.baudrate = 9600
        self.comm.serial.parity = serial.PARITY_NONE
        self.comm.serial.timeout = 0.2
        self.comm.serial.stopbits = 1
        self.comm.serial.bytesize = 8

    def _read(self, register, code=3, floatread=False):
        error_count = 0
        while error_count > -1:
            try:
                if floatread:
                    value = self.comm.read_float(register, functioncode=code)
                else:
                    value = self.comm.read_register(register, functioncode=code)
                error_count = -1
            except minimalmodbus.NoResponseError:
                time.sleep(0.5)
                error_count += 1
                if error_count > 10:
                    print('Error: {}'.format(error_count))
        return value

    def set_range(self, range_value):
        """
        Range is:
        0: '0-20',
        1: '0-200',
        2: '0-2000',
        3: '0-20000'
        """
        # Todo: check range is valid
        try:
            self.comm.write_register(
                value=range_value,
                registeraddress=5,
                functioncode=6
            )
        except minimalmodbus.NoResponseError:
            pass  # This exception is always raised
        time.sleep(1)
        updated_range = self.read_range()
        assert updated_range[0] == range_value
        return True

    def read_range(self):
        ranges = {
            0: '0-20',
            1: '0-200',
            2: '0-2000',
            3: '0-20000'
        }
        range_val = self._read(5)
        # print('Range: {}'.format(ranges[range_val]))
        return_val = (range_val, ranges[range_val])
        return return_val

    def read_conductivity(self):
        # todo: Implement auto-range
        conductivity = self._read(0, code=4, floatread=True)
        return conductivity

    def read_temperature(self):
         temperature = self._read(2, code=4, floatread=True)
         return temperature
    

if __name__ == '__main__':
    s411 = ChemitecS411()

    s411.set_range(0)
    range_val = s411.read_range()
    time.sleep(2)
    conductivity = s411.read_conductivity()
    temperature = s411.read_temperature()
    msg = 'Range is: {}, Value is: {}, temperature is: {}'
    print(msg.format(range_val[1], conductivity, temperature))

    s411.set_range(1)
    range_val = s411.read_range()
    time.sleep(2)
    conductivity = s411.read_conductivity()
    temperature = s411.read_temperature()
    msg = 'Range is: {}, Value is: {}, temperature is: {}'
    print(msg.format(range_val[1], conductivity, temperature))

    s411.set_range(2)
    range_val = s411.read_range()
    time.sleep(2)
    conductivity = s411.read_conductivity()
    temperature = s411.read_temperature()
    msg = 'Range is: {}, Value is: {}, temperature is: {}'
    print(msg.format(range_val[1], conductivity, temperature))
    
    # while True:
    #     conductivity = s411.read_conductivity()
    #     temperature = s411.read_temperature()
    #     msg = 'Conductivity: {}µS/cm. Temperature: {}C'
    #     print(msg.format(conductivity, temperature))
    
# inst_id = comm.read_register(0)
# print('Inst ID: {}'.format(hex(inst_id)))

# firmware = comm.read_register(1)
# print('Firmware Version: {}'.format(firmware))

# slave_id = comm.read_register(3)
# print('Slave ID: {}'.format(slave_id))

# filter_val = comm.read_register(4)
# print('Filter: {}'.format(filter_val))
