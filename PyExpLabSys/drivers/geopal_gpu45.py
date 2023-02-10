import serial
import minimalmodbus


class GeopalGP45(object):
    error_codes = {
        1: 'Alarm Low',
        2: 'Alarm High',
        3: 'Fault',
        4: 'Ok',
        5: 'No sensor'
    }

    def __init__(self, tty: str, instrument_address: int = 100):
        self.comm = self._setup_comm(instrument_address, tty)

    def _setup_comm(self, instrument_address: int, tty: str):
        comm = minimalmodbus.Instrument(tty, instrument_address)
        comm.serial.baudrate = 9600
        comm.serial.parity = serial.PARITY_EVEN
        comm.serial.timeout = 0.2
        comm.serial.stopbits = 1
        comm.serial.bytesize = 8
        return comm

    def _read(self, register):
        # todo: Add some error checks...
        value = self.comm.read_register(register, functioncode=3)
        return value

    def read_sensor(self, channel: int):
        value_register = channel * 100
        error_register = value_register + 1
        value = self._read(value_register)
        error_code = self._read(error_register)
        return value, error_code


if __name__ == '__main__':
    geopal = GeopalGP45('/dev/ttyUSB0')

    print(geopal.read_sensor(1))
    print(geopal.read_sensor(2))
    print(geopal.read_sensor(3))
    print(geopal.read_sensor(4))
    print(geopal.read_sensor(6))
