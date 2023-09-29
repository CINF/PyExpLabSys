from PyExpLabSys.drivers.inficon_sqm160 import InficonSQM160


class InficonSQC310(InficonSQM160):
    """ Driver for Inficon SQC310 QCM controller """

    def __init__(self, port='/dev/ttyUSB0'):
        super().__init__(baudrate=19200)

    def crystal_frequency_and_life(self, channel=1):
        """ Read crystal life """
        command = 'PA' + str(channel)
        value_string = self.comm(command)
        values_raw = value_string.split(b' ')
        active = values_raw[0] == b'1'
        frequency = float(values_raw[1])
        life = float(values_raw[2])
        return active, frequency, life

    def frequency(self, channel=1):
        _, frequency, _ = self.crystal_frequency_and_life(channel)
        return frequency

    def crystal_life(self, channel=1):
        _, _, life = self.crystal_frequency_and_life(channel)
        return life


if __name__ == '__main__':
    INFICON = InficonSQC310()

    print()
    print('Controler version: ', INFICON.show_version())

    print()
    print('Frequency and life 1: ', INFICON.crystal_frequency_and_life(1))
    print('Frequency and life 2: ', INFICON.crystal_frequency_and_life(2))

    print()
    print('Rate channel 1: ', INFICON.rate(1))
    print('Rate channel 2: ', INFICON.rate(2))

    print()
    print('Thinkness channel 1: ', INFICON.thickness(1))
    print('Thinkness channel 2: ', INFICON.thickness(2))
