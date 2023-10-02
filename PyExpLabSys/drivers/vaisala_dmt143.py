"""Driver for Vaisala DMT 143"""
import time
import serial


class VaisalaDMT143:
    """Driver for Vaisala DMT 143"""

    def __init__(self, port):
        self.serial = serial.Serial(
            port,
            baudrate=19200,
            timeout=1,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
        )
        self._init_device()

    def _init_device(self):
        self.comm(chr(27))  # stop continuous output
        # Set predictable output format;
        # dew_point; atm dew_point; vol_conc; status; addres; time since started
        self.comm(
            'FORM 3.6 Tdf ";" 3.6 Tdfa ";" 6.5 H2O ";" STAT ";" ADDR ";" TIME \\n'
        )

    def comm(self, command: str, single_line: bool = False) -> str:
        """
        Handle actual serial communication with instrument.
        """
        actual_command = (command + '\r').encode('ascii')
        try:
            self.serial.write(actual_command)
            if single_line:
                reply = self.serial.readline().decode()
            else:
                time.sleep(1)
                in_waiting = self.serial.inWaiting()
                reply = self.serial.read(in_waiting).decode()
        except OSError:
            reply = None
        return reply

    def device_information(self) -> dict:
        """
        Return information about the device.
        """
        command = '?'
        info_raw = self.comm(command)
        info = info_raw.strip()
        info = info.split('\n')
        model = info[0].strip()
        serial_nr = info[1].split(' ')[-1].strip()
        pressure = info[13].split(' ')[-2].strip()

        info_dict = {'model': model, 'serial_nr': serial_nr, 'pressure': pressure}
        return info_dict

    def current_errors(self):
        """
        Repport current error message, empty string if no errors.
        """
        command = 'ERRS'
        errors_raw = self.comm(command)
        if 'No errors' in errors_raw:
            error_list = ''
        else:
            error_list = errors_raw
        return error_list

    def set_reference_pressure(self, pressure: float):
        """
        Set reference pressure used for internal calculations.
        """
        command = 'XPRES {:.5f}'.format(pressure)
        reply = self.comm(command)
        print(reply)  # todo!

    def water_level(self):
        """
        The actual measurements from the device.
        """
        command = 'SEND'
        raw_value = self.comm(command, single_line=True)
        if raw_value is None:
            return
        split_values = raw_value.split(';')
        # print(split_values)

        dew_point = float(split_values[0])
        dew_point_atm = float(split_values[1])
        vol_conc = float(split_values[2])
        return_dict = {
            'dew_point': dew_point,  # C
            'dew_point_atm': dew_point_atm,
            'vol_conc': vol_conc,  # ppm
        }
        return return_dict


def main():
    """
    Main function, used only for test runs.
    """
    port = '/dev/ttyUSB0'
    dmt = VaisalaDMT143(port=port)

    current_errors = dmt.current_errors()
    if current_errors:
        print('Error! ' + current_errors)

    print(dmt.device_information())
    for i in range(0, 10):
        print(dmt.water_level())


if __name__ == '__main__':
    main()
