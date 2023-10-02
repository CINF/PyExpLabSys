import serial
import time
import signal
import sys


class DI2008(object):
    def __init__(self, port='/dev/ttyACM0', echo=True):
        self.ser = serial.Serial(port=port, baudrate=115200, timeout=0.1)
        self.acquiring = False
        self.stop()
        self.packet_size(0, echo=echo)  # 128 bytes packet size
        self.decimal(1)  # resets filter
        self.srate(4)
        self.slist_pointer = 0

    def comm(self, command, timeout=1, echo=True):
        prev = self.ser.read(self.ser.inWaiting())
        self.ser.write((command + '\r').encode())
        # If not acquiring, read reply from DI2008
        if not self.acquiring:
            time.sleep(0.1)
            # Echo commands if not acquiring
            t0 = time.time()
            while True:
                if time.time() - t0 > timeout:
                    return 'Timeout'
                if self.ser.inWaiting() > 0:
                    while True:
                        try:
                            s = self.ser.readline().decode()
                            s = s.strip('\n')
                            s = s.strip('\r')
                            s = s.strip(chr(0))
                            if echo:
                                print(repr(s))
                            break
                        except:
                            continue
                    if s != "":
                        if echo:
                            print(s)
                        return s.lstrip(command).strip()

    def device_name(self):
        self.comm('info 0')
        self.comm('info 1')

    def start(self):
        self.acquiring = True
        self.comm('start')

    def stop(self):
        self.acquiring = False
        self.comm('stop')

    def reset(self):
        self.comm('reset 1')

    def packet_size(self, value, echo=True):
        if value not in range(4):
            raise ValueError('Value must be 0, 1, 2, or 3.')
        psdict = {0: 16, 1: 32, 2: 64, 3: 128}
        self.ps = psdict[value]
        if echo:
            print('Packet size: {} B'.format(self.ps))
        self.comm('ps ' + str(value))

    def srate(self, value):
        value = int(value)
        if value >= 4 and value <= 2232:
            self.comm('srate ' + str(value))
            self.sr = value
        else:
            raise ValueError('Value SRATE out of range')

    def decimal(self, value):
        value = int(value)
        if value >= 1 and value <= 32767:
            self.comm('dec ' + str(value))
            self.dec = value
        else:
            raise ValueError('Value DEC out of range')

    def set_filter(self, channel, mode='average'):
        if channel not in [0, 1, 2, 3, 4]:
            raise ValueError('Channel must be 1, 2, 3 or 4. Or 0 for all channels')
        if mode not in ['last point', 'average', 'max', 'min']:
            mode = 'average'
            raise Warning('mode was not recognized, mode=average is used')
        filter_dict = {'last point': 0, 'average': 1, 'max': 2, 'min': 3}
        if channel == 0:
            self.comm('filter * ' + str(filter_dict[mode]))
        else:
            self.comm('filter ' + str(channel - 1) + ' ' + str(filter_dict[mode]))
        if not hasattr(self, 'channel_filter'):
            self.channel_filter = {}
        self.channel_filter[channel] = mode

    def add_voltage_analog_channel(self, channel, voltage=5.0, echo=True):
        # channels 1, 2, 3, and 4, are enabled. If the more expensive 8-channel daq is purchased, this function should be expanded
        # voltage is in volts
        if channel not in [1, 2, 3, 4, 5, 6, 7, 8]:
            raise ValueError('Channel must be between 1 and 8.')
        if voltage not in [
            0.01,
            0.025,
            0.05,
            0.1,
            0.25,
            0.5,
            1.0,
            2.5,
            5.0,
            10.0,
            25.0,
            50.0,
        ]:
            raise ValueError('Cannot measure chosen voltage.')
        if not hasattr(self, 'channel_voltage'):
            self.channel_voltage = {}
        self.channel_voltage[channel] = voltage
        if not hasattr(self, 'slist_pointer_to_channel'):
            self.slist_pointer_to_channel = {}
        self.slist_pointer_to_channel[self.slist_pointer] = channel
        voltage_dict = {
            0.5: '0',
            0.25: '1',
            0.1: '2',
            0.05: '3',
            0.025: '4',
            0.01: '5',  # 6 and 7 are undefined
            50.0: '8',
            25.0: '9',
            10.0: 'A',
            5.0: 'B',
            2.5: 'C',
            1.0: 'D',
        }
        self.comm(
            'slist '
            + str(self.slist_pointer)
            + ' '
            + str(int('0x0' + voltage_dict[voltage] + '0' + str(channel - 1), 16))
        )  # writes command in hex-bit and translate to number
        self.slist_pointer += 1
        self.comm('filter ' + str(channel - 1) + ' 0')
        # 0x[3 bits for voltage][one bit for channel]
        # 0x0A00 = 2560 is 10V on channel 1
        # 0x0B01 = 2817 is 5V on channel 2
        # 0x0C02 = 3074 is 2.5V on channel 3
        # 0x0D03 = 3331 is 1V on channel 4
        if not hasattr(self, 'dec'):
            self.decimal(1)
        if not hasattr(self, 'sr'):
            self.srate(4)
        if echo:
            print(
                'Analog channel ' + str(channel) + ' measure +-' + str(voltage) + ' V'
            )

    def read(self):
        output = {}
        for pointer in range(self.slist_pointer):
            byte = self.ser.read(2)
            result = (
                self.channel_voltage[self.slist_pointer_to_channel[pointer]]
                * int.from_bytes(byte, byteorder='little', signed=True)
                / 32768
            )
            output[self.slist_pointer_to_channel[pointer]] = round(result, 4)
        slist_pointer = 0
        return output


if __name__ == '__main__':
    dev = DI2008()
    dev.device_name()
    dev.add_voltage_analog_channel(1, voltage=0.01)
    dev.add_voltage_analog_channel(2, voltage=1.0)
    dev.add_voltage_analog_channel(3, voltage=5.0)
    dev.add_voltage_analog_channel(4, voltage=10.0)
    # dev.decimal(3)
    # dev.set_filter(0,mode='average')
    dev.start()
    for n in range(10000):
        data = dev.read()
        print(round(data[1], 3), round(data[3], 3), round(data[4], 3))
        time.sleep(0.005)
    dev.stop()
