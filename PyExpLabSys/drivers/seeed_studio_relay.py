import time
import smbus

bus = smbus.SMBus(1)


class i2c_relay:
    global bus

    def __init__(self):
        self.address = 0x20
        self.reg_mode = 0x06
        self.reg_data = 0xFF
        self.write_bus()

    def write_bus(self):
        bus.write_byte_data(self.address, self.reg_mode, self.reg_data)

    def ON(self, num, echo=False):
        if num not in [1, 2, 3, 4]:
            raise ValueError(
                'No relay port numbered ',
                num,
                ' available. Please specify a number from 1 to 4.',
            )
        if echo:
            print('Turning relay', num, 'ON')
        self.reg_data &= ~(0x1 << (num - 1))
        self.write_bus()

    def OFF(self, num, echo=False):
        if num not in [1, 2, 3, 4]:
            raise ValueError(
                'No relay port numbered ',
                num,
                ' available. Please specify a number from 1 to 4.',
            )
        if echo:
            print('Turning relay', num, 'OFF')
        self.reg_data |= 0x1 << (num - 1)
        self.write_bus()


if __name__ == '__main__':
    relay = i2c_relay()
    for i in [1, 2, 3, 4]:
        relay.ON(i)
        time.sleep(0.5)
    for i in [1, 2, 3, 4]:
        relay.OFF(i)
        time.sleep(0.5)
