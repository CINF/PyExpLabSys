import time

import pyvisa
import numpy as np
import matplotlib.pyplot as plt


class Infinii:
    def __init__(self, visa_addr):
        rm = pyvisa.ResourceManager()
        self.instr = rm.open_resource(visa_addr)
        self.instr.timeout = 10000
        print(self.instr.query('*IDN?'))
        self.instr.write('WAVeform:FORMat WORD')

    def _read_preamble(self):
        # We do not provide a channel since this is used in connection
        # with waveform acquistion where channel has already been cosen.
        preamble_raw = self.instr.query(':WAVeform:PREamble?').split(',')
        preamble = {
            'format': int(preamble_raw[0]),  # 0: byte, 1: WORD, 4: ascii
            'meas_type': int(preamble_raw[1]),  # 0: Average, 0: Normal, 1: Peak detect
            'points': int(preamble_raw[2]),  # Possibly not used
            'count': int(preamble_raw[3]),  # Number of spectra in average
            'x_increment': float(preamble_raw[4]),
            'x_origin': float(preamble_raw[5]),
            'x_reference': float(preamble_raw[6]),  # Int?
            'y_increment': float(preamble_raw[7]),
            'y_origin': float(preamble_raw[8]),
            'y_reference': int(preamble_raw[9]),
        }
        return preamble

    def read_cursor_positions(self):
        # Not yet implemented
        pass

    def get_waveform(self, channel):
        if not channel in (1, 2, 3, 4):
            return
        scope.instr.write('WAVeform:SOURce CHANnel{}'.format(channel))

        preamble = self._read_preamble()
        print('Preamble: ', preamble)

        # The stated datatype and endianess is correct for now,
        # but this should be explicitly defined in __init__
        # print(self.instr.query('WAVeform:FORMat?'))
        t = time.time()
        y_data_raw = self.instr.query_binary_values(
            'WAVeform:DATA?', datatype='H', is_big_endian=True
        )
        print('Total measurement time: {:.2f}s'.format(time.time() - t))

        y_data = np.zeros(len(y_data_raw))
        for i in range(0, len(y_data)):
            y_data[i] = (y_data_raw[i] - preamble['y_reference']) * preamble[
                'y_increment'
            ] + preamble['y_origin']

        x_data = (
            np.arange(-0.5 * len(y_data), 0.5 * len(y_data))
            * preamble['x_increment']
            # +  preamble['y_increment']  # Handle delay
        )
        return x_data, y_data


if __name__ == '__main__':
    # If in doubt about the address, see the list of devices here:
    # rm = pyvisa.ResourceManager()
    # resources = rm.list_resources()
    # print(resources)
    # exit()

    visa_addr = 'USB0::10893::5990::MY56311274::0::INSTR'
    scope = Infinii(visa_addr)

    x_data1, y_data1 = scope.get_waveform(1)

    fig = plt.figure()
    axis = fig.add_subplot(1, 1, 1)

    (line_data1,) = axis.plot(x_data1, y_data1, 'y.')

    plt.show()
