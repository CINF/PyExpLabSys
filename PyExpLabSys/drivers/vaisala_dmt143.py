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

    def comm(self, command):
        """
        Handle actual serial communication with instrument.
        """
        actual_command = (command + "\r").encode("ascii")
        self.serial.write(actual_command)
        time.sleep(1)
        in_waiting = self.serial.inWaiting()
        reply = self.serial.read(in_waiting).decode()
        return reply

    def device_information(self):
        """
        Return information about the device.
        """
        command = "?"
        info_raw = self.comm(command)
        info = info_raw.strip()
        info = info.split("\n")
        model = info[0].strip()
        serial_nr = info[1].split(" ")[-1].strip()
        pressure = info[13].split(" ")[-2].strip()

        # for item in info:
        #    print(item.strip())

        info_dict = {"model": model, "serial_nr": serial_nr, "pressure": pressure}
        return info_dict

    def current_errors(self):
        """
        Repport current error message, empty string if no errors.
        """
        command = "ERRS"
        errors_raw = self.comm(command)
        if "No errors" in errors_raw:
            error_list = ""
        else:
            error_list = errors_raw
        return error_list

    def set_reference_pressure(self, pressure: float):
        """
        Set reference pressure used for internal calculations.
        """
        command = "XPRES {:.5f}".format(pressure)
        reply = self.comm(command)
        print(reply)  # todo!

    def water_level(self):
        """
        The actual measurements from the device.
        """
        command = "SEND"
        raw_value = self.comm(command)
        # One could consider to use the FORMAT command
        # to make the output less cryptic...
        split_values = raw_value.split(" ")
        dew_point = float(split_values[2])
        dew_point_atm = float(split_values[6])
        vol_conc = float(split_values[9])
        return_dict = {
            "dew_point": dew_point,
            "dew_point_atm": dew_point_atm,
            "vol_conc": vol_conc,
        }
        return return_dict


def main():
    """
    Main function, used only for test runs.
    """
    port = "/dev/ttyUSB0"
    dmt = VaisalaDMT143(port=port)

    # print(dmt.set_reference_pressure(1))
    current_errors = dmt.current_errors()
    if current_errors:
        print("Error! " + current_errors)

    # print(dmt.device_information())
    print(dmt.water_level())


if __name__ == "__main__":
    main()
