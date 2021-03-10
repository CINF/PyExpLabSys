import time
import serial


class PowerWalker(object):
    """
    https://networkupstools.org/protocols/megatec.html
    Apparantly, for the available model, none of the control works.
    """
    def __init__(self, port='/dev/ttyUSB2'):
        self.serial = serial.Serial(
            port=port,
            baudrate=2400,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1
        )

    def comm(self, command, start_byte):
        error = 0
        while -1 < error < 10:
            command = command + '\r'
            self.serial.write(command.encode())
            reply_raw = self.serial.readline()
            reply = reply_raw.decode()

            if not (reply[0] == start_byte and reply[-1] == '\r'):
                self.serial.flush()
                time.sleep(0.25)
                error += 1
            else:
                error = -1

        if error > -1:
            raise RuntimeError('Communication error with UPS')

        reply = reply[1:-1]
        return reply

    def device_information(self):
        reply = self.comm('I', '#')
        information = {
            'company': reply[0:15].strip(),
            'model': reply[16:26].strip(),
            'version': reply[27:].strip()
        }
        return information

    def device_ratings(self):
        reply = self.comm('F', '#')
        values = reply.split(' ')
        ratings = {
            'rated_voltage': float(values[0]),
            'rated_current': float(values[1]),
            'battery_voltage': float(values[2]),
            'rated_frequency': float(values[3]),
        }
        return ratings

    def device_status(self):
        reply = self.comm('Q1', '(')
        values = reply.split(' ')

        bat_volt_string = values[5]
        # For on-line units battery voltage/cell is provided in the form S.SS.
        # For standby units actual battery voltage is provided in the form SS.S.
        # UPS type in UPS status will determine which reading was obtained.
        ups_status = []
        status_description = {  # Todo, add e
            0: 'Beeper On',
            1: 'Shutdown Active',
            2: 'Test in Progress',
            3: 'Standby',  # Otherwise: Online
            4: 'UPS Failed',
            5: 'Bypass/Boost or Buck Active',
            6: 'Battery Low',
            7: 'Utility Fail'
        }

        status_string = values[7]
        for i in range(0, 8):
            bit_value = (status_string[-1 - i] == '1')
            if bit_value:
                ups_status.append(status_description[i])

        status = {
            'input_voltage': float(values[0]),
            'input_fault_voltage': float(values[1]),
            'output_voltage': float(values[2]),
            'output_current': float(values[3]),
            'input_frequency': float(values[4]),
            'battery_voltage': float(values[5]),
            'temperature': float(values[6]),
            'status': ups_status,
        }
        return status


if __name__ == '__main__':
    pw = PowerWalker()
    print(pw.device_status())
    print(pw.device_information())
    print(pw.device_ratings())
