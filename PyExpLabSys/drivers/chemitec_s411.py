import time
import serial
import minimalmodbus

try:
    import wiringpi as wp
except ImportError:
    pass  # Will not be able to use DirectionalSerial


class DirectionalSerial(serial.Serial):
    def __init__(self, direction_pin, **kwargs):  # Remove default
        super().__init__(**kwargs)
        wp.wiringPiSetup()
        wp.pinMode(direction_pin, 1)
        self.direction_pin = direction_pin

    def write(self, request):
        sleep_length = 0.01 + 1.0 * len(request) / self.baudrate
        wp.digitalWrite(self.direction_pin, 1)
        super().write(request)
        time.sleep(sleep_length)
        wp.digitalWrite(self.direction_pin, 0)


class ChemitecS411(object):
    def __init__(self, tty, instrument_address=18, gpio_dir_pin=None):
        self.gpio_dir_pin = gpio_dir_pin
        if instrument_address > 0:
            self.comm = self._setup_comm(instrument_address, tty)
        else:
            # In this case we scan for instruments and return
            for address in range(1, 255):
                success = False
                for i in range(0, 3):
                    self.comm = self._setup_comm(address, tty=tty)
                    try:
                        value = self.comm.read_float(2, functioncode=4)
                        msg = 'Found instrument at {}, temperature is {:.1f}C'
                        print(msg.format(address, value))
                        success = True
                        break
                    except minimalmodbus.NoResponseError:
                        pass
                if not success:
                    print('No instrument found at {}'.format(address))

    def _setup_comm(self, instrument_address, tty):
        comm = minimalmodbus.Instrument(tty, instrument_address)
        # if True:  # Add init-option here:
        if self.gpio_dir_pin:
            dir_serial = DirectionalSerial(
                port=tty,
                baudrate=19200,
                parity=serial.PARITY_NONE,
                bytesize=8,
                stopbits=1,
                timeout=0.05,
                write_timeout=2.0,
                direction_pin=self.gpio_dir_pin,
            )
            comm.serial = dir_serial

        comm.serial.baudrate = 9600
        comm.serial.parity = serial.PARITY_NONE
        comm.serial.timeout = 0.2
        comm.serial.stopbits = 1
        comm.serial.bytesize = 8
        return comm

    def _read(self, register, code=3, floatread=False, keep_trying=False):
        error_count = 0
        while error_count > -1:
            try:
                if floatread:
                    value = self.comm.read_float(register, functioncode=code)
                else:
                    value = self.comm.read_register(register, functioncode=code)
                error_count = -1
            except minimalmodbus.NoResponseError:
                time.sleep(0.2)
                error_count += 1
                if error_count > 1000:
                    if keep_trying:
                        print('Error: {}'.format(error_count))
                    else:
                        break
        return value

    def _write(self, value, registeraddress):
        try:
            self.comm.write_register(
                value=value, registeraddress=registeraddress, functioncode=6
            )
        except minimalmodbus.NoResponseError:
            pass  # This exception is always raised after write
        return True

    def read_firmware_version(self):
        version = self._read(1, code=3)
        actual_version = version / 10.0
        return actual_version

    def read_filter_value(self):
        """
        Return the current low-pass filter, range is 0-16, units unknown.
        0: No filter, 16: maximum filtering
        """
        filter_code = self._read(4, code=3)
        return filter_code

    def read_range(self):
        ranges = {0: '0-20', 1: '0-200', 2: '0-2000', 3: '0-20000'}
        range_val = self._read(5)
        # print('Range: {}'.format(ranges[range_val]))
        return_val = (range_val, ranges[range_val])
        return return_val

    def read_serial(self):
        """
        Returns the serial number of the unit.
        """
        serial_nr = '{}{}{}{}'.format(
            self._read(9, code=3),
            self._read(10, code=3),
            self._read(11, code=3),
            self._read(12, code=3),
        )
        return serial_nr

    def set_instrument_address(self, instrument_address):
        """
        Legal values are 1-255
        """
        self._write(instrument_address, 3)

        self.comm = self._setup_comm(instrument_address)
        print(self.read_serial())
        return True

    def set_filter(self, filter_value):
        """
        Legal values are 0-16
        """
        self._write(filter_value, 4)
        updated_filter = self.read_filter_value()
        assert updated_filter == filter_value
        return True

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
                value=range_value, registeraddress=5, functioncode=6
            )
        except minimalmodbus.NoResponseError:
            pass  # This exception is always raised
        time.sleep(1)
        updated_range = self.read_range()
        assert updated_range[0] == range_value
        return True

    def read_conductivity(self):
        conductivity = self._read(0, code=4, floatread=True)
        return conductivity

    def read_temperature(self):
        temperature = self._read(2, code=4, floatread=True)
        return temperature

    def read_conductivity_raw(self):
        """
        Returns raw conductivity value, range 0-2500mV
        """
        conductivity = self._read(4, code=4, floatread=True)
        return conductivity

    def read_temperature_raw(self):
        """
        Returns raw temperature measurement value, range 0-5000mV
        """
        temperature = self._read(6, code=4, floatread=True)
        return temperature

    def read_calibrations(self):
        """
        Internal calibration values. These are range-dependent.
        Setting calibrations is also possible, but this is not currently
        implemented.
        """
        calibrations = {
            'manual_temperature': self._read(8, code=4, floatread=True),
            'temperature_offset': self._read(10, code=4, floatread=True),
            'cal2_val_user': self._read(12, code=4, floatread=True),
            'cal2_mis_user': self._read(14, code=4, floatread=True),
            'cal2_val_default': self._read(16, code=4, floatread=True),
            'cal2_mis_default': self._read(18, code=4, floatread=True),
        }
        return calibrations


if __name__ == '__main__':
    # s411 = ChemitecS411(instrument_address=0, tty='/dev/serial1')
    # s411 = ChemitecS411(instrument_address=0, tty='/dev/ttyUSB0')
    # exit()
    # s411 = ChemitecS411(instrument_address=15, tty='/dev/ttyUSB0')
    s411 = ChemitecS411(instrument_address=15, tty='/dev/serial1', gpio_dir_pin=13)

    print(s411.read_serial())
    print(s411.read_firmware_version())
    print(s411.read_filter_value())
    print()
    print(s411.read_conductivity())
    print(s411.read_conductivity_raw())
    print(s411.read_temperature())
    print(s411.read_temperature_raw())
    print(s411.read_calibrations())
    print()
    s411.set_range(0)
    range_val = s411.read_range()
    time.sleep(2)
    conductivity = s411.read_conductivity()
    temperature = s411.read_temperature()
    msg = 'Range is: {}, Value is: {}, temperature is: {}'
    print(msg.format(range_val[1], conductivity, temperature))
