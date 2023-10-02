import time
import smbus


class SparkFunQuadRelay:
    """Driver for the QWIIC SparkFun Quad Relay """

    def __init__(self, address=0x6D):
        # Get I2C bus
        self.bus = smbus.SMBus(1)
        self.device_address = address

    def set_relay(self, relay_index, wanted_state):
        assert relay_index in range(1, 5)

        current_state = self.relay_status(relay_index)

        if not current_state == wanted_state:
            self.bus.write_byte(self.device_address, relay_index)
        return True

    def relay_status(self, relay_index):
        reply = self.bus.read_byte_data(self.device_address, 4 + relay_index)
        return reply > 0


if __name__ == '__main__':
    relay = SparkFunQuadRelay()

    relay.set_relay(4, False)
    time.sleep(1.0)
    print(relay.relay_status(4))
