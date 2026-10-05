import time

import pyvisa
import numpy as np
import matplotlib.pyplot as plt


class TektronixTDS:
    # Docs: https://mmrc.caltech.edu/Oscilliscope/TDS200%20Programer.pdf

    def __init__(self, visa_addr):
        rm = pyvisa.ResourceManager()
        self.instr = rm.open_resource(visa_addr)
        self.usb_scope = True
        if 'ASRL' in visa_addr:
            self.usb_scope = False
            self.instr.baud_rate = 9600
            self.instr.parity = pyvisa.constants.Parity.none
            self.instr.timeout = 25000
        else:
            self.instr.timeout = 1000

        # Slow but reliable, use for all communnication except actual data
        self.instr.write('DATa:ENCdg ASCIi')
        self.instr.write('DATa:WIDth 1')

        print(self.instr.query('*IDN?'))
        self.sample_interval = self.v_scale = self.v_offset = self.delay = None

    def _update_scale_info(self):
        """
        Ask the instrument for the screen parameters.
        This is a primitive implementation where each parameter is read
        one-by-one. We could also get all information in one go.
        """
        self.sample_interval = float(self.instr.query('WFMPre:XINcr?'))
        # These will be a lists, since each channel can be different
        self.v_scale = float(self.instr.query('WFMPre:YMUlt?'))
        self.v_offset = float(self.instr.query('WFMPre:YOFf?')) * self.v_scale
        self.delay = float(self.instr.query('HORizontal:MAIn:POSition?'))
        return self.sample_interval, self.v_scale, self.v_offset, self.delay

    def read_cursor_positions(self):
        positions_raw = self.instr.query('CURSor:VBArs?').split(';')
        # First item is the word 'SECONDS'
        pos1 = float(positions_raw[1])
        pos2 = float(positions_raw[2])
        time_positions = (pos1, pos2)

        positions_raw = self.instr.query('CURSor:HBArs?').split(';')
        # First item is the word 'VOLTS'
        pos1 = float(positions_raw[1])
        pos2 = float(positions_raw[2])
        volt_positions = (pos1, pos2)

        return time_positions, volt_positions

    def get_waveform(self, channel=1):
        """
        Retrive a full waveform. X-axis is generated from number of
        samples and self.sample_interval. Trigger point is currently
        not registred.
        """
        if channel == 1:
            ch_txt = 'CH1'
        elif channel == 2:
            ch_txt = 'CH2'
        else:
            print('Invalid channel')
            return

        enabled = int(self.instr.query('SELect:{}?'.format(ch_txt)))
        if enabled == 0:
            return [], []

        source = self.instr.query('DATa:SOUrce?').strip()
        if not (ch_txt == source):
            print('Update scale', ch_txt)
            self.instr.write('DATa:SOUrce {}'.format(ch_txt))
            self._update_scale_info()
        if self.v_scale is None:
            self._update_scale_info()

        t = time.time()
        binary = self.usb_scope
        if binary:
            self.instr.write('DATa:ENCdg RIBinary')  # This is much faster than ascii
            self.instr.write('DATa:WIDth 2')
            y_data_raw = self.instr.query_binary_values(
                'CURVe?', datatype='h', is_big_endian=True
            )
            # self.instr.read_raw() # Binary read leaves an extra newline that must be read
            # ....or not
            self.instr.write('DATa:ENCdg ASCIi')
            self.instr.write('DATa:WIDth 1')

            y_data = np.zeros(len(y_data_raw))
            for i in range(0, len(y_data)):
                y_data[i] = (y_data_raw[i] / 256.0) * self.v_scale - self.v_offset

        else:  # ascii mode
            y_data_raw = self.instr.query('CURVe?').split(',')
            y_data = np.zeros(len(y_data_raw))
            for i in range(0, len(y_data)):
                y_data[i] = int(y_data_raw[i]) * self.v_scale - self.v_offset

        print('Total measurement time: {:.2f}s'.format(time.time() - t))
        x_data = (
            np.arange(-0.5 * len(y_data), 0.5 * len(y_data)) * self.sample_interval
            + self.delay
        )
        return x_data, y_data


if __name__ == '__main__':
    # If in doubt about the address, see the list of devices here:
    # rm = pyvisa.ResourceManager()
    # resources = rm.list_resources()
    # print(resources)
    # exit()

    # visa_addr = 'ASRL/dev/ttyUSB0::INSTR'
    visa_addr = 'USB0::1689::871::C062935::0::INSTR'
    tds = TektronixTDS(visa_addr)

    # Returns two two-position tuples, in this exercise we only make use if the first one
    cursors = tds.read_cursor_positions()
    time_pos = cursors[0]

    x_data1, y_data1 = tds.get_waveform(1)
    x_data2, y_data2 = tds.get_waveform(2)

    fig = plt.figure()
    axis = fig.add_subplot(1, 1, 1)

    (line_data1,) = axis.plot(x_data1, y_data1, 'y-')
    (line_data2,) = axis.plot(x_data2, y_data2, 'b-')

    axis.axvline(time_pos[0])
    axis.axvline(time_pos[1])

    plt.show()
