import time
import crc16
import serial

import usb


class PowerWalker(object):
    """
    https://networkupstools.org/protocols/megatec.html
    Apparantly, for the available model, none of the control works.
    """

    def comm(self, command, start_byte):
        raise NotImplementedError

    def device_information(self):
        reply = self.comm('I', '#')
        information = {
            'company': reply[0:15].strip(),
            'model': reply[16:26].strip(),
            'version': reply[27:].strip(),
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
        values = []
        errors = 0
        while -1 < errors < 10:
            reply = self.comm('Q1', '(')
            # print('Reply: {}'.format(reply))
            values = reply.split(' ')
            try:
                assert len(values) == 8
                assert len(values[7]) == 8
                errors = -1
            except AssertionError:
                errors += 1
                time.sleep(0.01)
        # print(values)
        if errors > 0:
            raise Exception('Unable to get status from UPS!')
        # bat_volt_string = values[5]
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
            7: 'Utility Fail',
        }

        status_string = values[7]
        for i in range(0, 8):
            bit_value = status_string[-1 - i] == '1'
            if bit_value:
                ups_status.append(status_description[i])

        status = {
            'input_voltage': float(values[0]),
            'input_fault_voltage': float(values[1]),
            'output_voltage': float(values[2]),
            'output_current': float(values[3]) / 10,
            'input_frequency': float(values[4]),
            'battery_voltage': float(values[5]),
            'temperature': float(values[6]),
            'status': ups_status,
        }
        return status


class PowerWalkerUsb(PowerWalker):
    def __init__(self, port='/dev/ttyUSB0'):
        # USB reverse engineering by
        # allican.be/blog/2017/01/28/reverse-engineering-cypress-serial-usb.html
        vendorId = 0x0665
        productId = 0x5161
        interface = 0
        self.dev = usb.core.find(idVendor=vendorId, idProduct=productId)
        if self.dev.is_kernel_driver_active(interface):
            self.dev.detach_kernel_driver(interface)
            self.dev.set_interface_altsetting(0, 0)

    def getCommand(self, cmd):
        cmd = cmd.encode('utf-8')
        crc = crc16.crc16xmodem(cmd).to_bytes(2, 'big')
        cmd = cmd + crc
        cmd = cmd + b'\r'
        while len(cmd) < 8:
            cmd = cmd + b'\0'
        return cmd

    def sendCommand(self, cmd):
        self.dev.ctrl_transfer(0x21, 0x9, 0x200, 0, cmd)

    def getResult(self, timeout=100):
        res = ""
        i = 0
        while '\r' not in res and i < 20:
            try:
                res += "".join(
                    [chr(i) for i in self.dev.read(0x81, 8, timeout) if i != 0x00]
                )
            except usb.core.USBError as e:
                if e.errno == 110:
                    pass
                else:
                    raise
            i += 1
        return res

    def comm(self, command, start_byte):
        self.sendCommand(self.getCommand(command + '\r'))
        res = self.getResult()
        reply = res[1:-1]
        return reply


class PowerWalkerSerial(PowerWalker):
    def __init__(self, port='/dev/ttyUSB0'):
        self.serial = serial.Serial(
            port=port,
            baudrate=2400,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=1,
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


if __name__ == '__main__':
    pw = PowerWalkerSerial()
    # pw = PowerWalkerUsb()
    print(pw.device_status())
    print(pw.device_information())
    print(pw.device_ratings())
