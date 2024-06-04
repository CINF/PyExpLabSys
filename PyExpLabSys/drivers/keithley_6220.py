""" Simple driver for Keithley 6220 SMU """
import time

import pyvisa


class Keithley6220:
    """
    Simple driver for Keithley 6200 SMU
    Actual implementation performed on a 6221 - please
    double check if you have a 6220.
    """

    def __init__(self, interface, path=''):
        rm = pyvisa.ResourceManager('@py')
        if interface == 'serial':
            pass
        if interface == 'gpib':
            pass
        if interface == 'lan':
            conn_string = 'TCPIP0::{}::1394::SOCKET'.format(path)
            # 6221 is apparantly not VXI compatible: no ::INSTR connection
            self.instr = rm.open_resource(conn_string)
            self.instr.read_termination = '\n'
            self.instr.write_termination = '\n'

        self.latest_error = []
        # Set error format to binary and clear queue
        self.instr.write('FORMAT:SREGISTER BINARY')
        self.instr.query('*ESR?')
        self.instr.write('*cls')

    def _check_register(self, command: str, msg=None):
        magic_messages = {
            ('STATUS:QUESTIONABLE:EVENT?', 4): 'Questionable Power',
            ('STATUS:QUESTIONABLE:EVENT?', 8): 'Questionable Calibration',
            ('STATUS:MEASUREMENT:EVENT?', 2): 'Internal temperature too high',
            ('STATUS:MEASUREMENT:EVENT?', 3): 'Voltage complicance',
            ('*ESR?', 4): 'Setpoint out of current range',
        }
        if msg is None:
            msg = command
        register_ok = True
        status_string = self.instr.query(command)
        # Reverse string to count from 0 to N
        bit_string = status_string[::-1]
        for i in range(0, len(bit_string)):
            # print('{}: {}'.format(i, esr[i]))
            if bit_string[i] == '1':
                register_ok = False
                error_string = magic_messages.get((command, i))
                if error_string is None:
                    error_string = '{} error in bit: {}'.format(msg, i)
                self.latest_error.append(error_string)
        return register_ok

    def read_error_queue(self):
        error_list = {}
        error = 1
        while error > 0:
            next_error = self.instr.query('STATUS:QUEUE:NEXT?')
            try:
                error_raw, msg = next_error.split(',')
            except ValueError:
                print('Error! ', next_error)
                error_raw = 0
            error = int(error_raw)
            if error > 0:
                if error in error_list:
                    error_list[error]['count'] += 1
                else:
                    error_list[error] = {'count': 1, 'msg': msg}
        return error_list

    def read_status(self):
        status_ok = True
        registers = {
            '*ESR?': 'Standard Event Status',
            # 'STATUS:MEASUREMENT:CONDITION?': 'Measurement Condition Register',
            # '*STB?': 'Status Byte Register',
            'STATUS:MEASUREMENT:EVENT?': 'Measurement Event Register',
            'STATUS:QUESTIONABLE:EVENT?': 'Questionable Event Register',
        }
        for command, message in registers.items():
            status_ok = status_ok & self._check_register(command, message)

        error_queue = self.read_error_queue()
        if error_queue:
            status_ok = False
            for error in error_queue.values():
                self.latest_error.append(error['msg'])
        # Operation Event Register - apparantly only available doing sweeps:
        # 'STATUS:OPERATON:EVENT?'

        # This seems to be a summary. If performance is a problem, it can be
        # used to check if other conditions needs to be checked.
        # Service Request Enable: '*SRE?'
        if status_ok:
            self.latest_error = []
        return status_ok

    def output_state(self, output_state: bool = None):
        """Turn the output on or off"""
        if output_state is not None:
            if output_state:
                self.instr.write('OUTPUT ON')
            else:
                self.instr.write('OUTPUT OFF')

        error = 0
        while -1 < error < 10:
            try:
                actual_state_raw = self.instr.query('OUTPUT?')
                actual_state = int(actual_state_raw[0]) == 1
                error = -1
            except ValueError:
                print('output state error ', repr(actual_state_raw))
                error = error + 1
        # This will fail if error exceeds 10, let's see if it happens
        return actual_state

    def set_current_range(self, current_range: float = None):
        """
        This device can only source current, not voltage.
        Currently we set both DC and AC range at the same time
        """
        if current_range is not None:
            self.instr.write('CURRENT:RANGE {}'.format(current_range))
            self.instr.write('SOURCE:WAVE:RANGING FIXED')
        actual_range_raw = self.instr.query('CURRENT:RANGE?')
        actual_range = float(actual_range_raw)
        return actual_range

    def set_voltage_limit(self, voltage: float = None):
        """Set the desired voltate limit"""
        if voltage is not None:
            self.instr.write('CURRENT:COMPLIANCE {:.9f}'.format(voltage))
        actual = self.instr.query('CURRENT:COMPLIANCE?')
        return actual

    def set_current(self, current: float):
        """Set the DC current, when not performing a waveform"""
        self.instr.write('CURRENT {:.12f}'.format(current))
        return True

    def set_wave_amplitude(self, amplitude: float):
        cmd = 'SOUR:WAVE:AMPL {:.9f}'.format(amplitude)
        self.instr.write(cmd)
        return True

    def source_sine_wave(self, frequency, amplitude):
        self.instr.write('SOUR:WAVE:FUNC SIN')
        self.instr.write('SOUR:WAVE:FREQ {}'.format(frequency))
        # self.scpi_comm('SOUR:WAVE:AMPL {}'.format(1e-11))
        self.instr.write('SOUR:WAVE:AMPL {}'.format(amplitude))
        self.instr.write('SOUR:WAVE:OFFS 0')  # Offset
        self.instr.write('SOUR:WAVE:PMAR:STAT ON')
        self.instr.write('SOUR:WAVE:PMAR 0')
        self.instr.write('SOUR:WAVE:PMAR:OLIN 6')
        self.instr.write('SOUR:WAVE:DUR:TIME INF')
        # self.scpi_comm('SOUR:WAVE:RANG BEST')
        self.instr.write('SOUR:WAVE:ARM')
        self.instr.write('SOUR:WAVE:AMPL {}'.format(amplitude))
        self.instr.write('SOUR:WAVE:INIT')

    # TODO - CAN WE PROGRAMMATICALLY CHOOSE BETWEEN THESE
    # FOR ONE COMMON FUNCTION?
    def stop_and_unarm_wave(self):
        self.instr.write('SOURCE:WAVE:ABORT')

    def stop_and_unarm_sweep(self):
        # This now has two names - same as end_delta_measurement!!!!!!!
        self.instr.write('SOURCE:SWEEP:ABORT')

    def read_diff_conduct_line(self):
        try:
            t = time.time()
            buf_actual = int(self.instr.query('TRACe:POINTs:ACTual?').strip())
            print(' K6220: Read buffer: {}'.format(time.time() - t))

        except ValueError:
            buf_actual = 0
        print('Buf: ', buf_actual)
        if buf_actual > 0:
            t = time.time()
            data = self.instr.query('SENS:DATA:FRESH?').strip()
            print(' K6220: Read data: {}'.format(time.time() - t))
        else:
            print('No data')
            return {}
        row = {}
        if len(data) < 5:
            return {}

        fields = data.split(',')
        try:
            row = {
                'reading': float(fields[0][:-3]),
                'time': float(fields[1][:-4]),
                'current': float(fields[2][:-3]),
                'avoltage': float(fields[3][:-3]),
                'compliance_ok': fields[4][0] == 'F',
                'reading_nr': int(fields[5][1:6]),
            }
            # print(row)
        except ValueError:
            # Could we do a fancy split based on the units even if errors exists in the
            # field delimiters?
            # +1.01194701E-05VDC+1.01928472E-05VDC,+1.471E+00SECS,+1.0000E-06ADC,+2.03093674E-04VDC,FCMPL,+22698RDNG#
            print('Error in row: {}'.format(data))
        return row

    def perform_differential_conductance_measurement(
        self, start, stop, steps, delta, v_limit=1.5, nplc=5
    ):
        step_size = (stop - start) / steps
        # print('Number of steps: {}'.format(steps))
        print('K6220 driver: steps size: {}'.format(step_size))

        # 1) Configure 2182a?
        # print('2182a present, ', self.scpi_comm('SOURCE:DELTA:NVPResent?'))
        # self.reset_device()  # Is this needed?
        # time.sleep(1)
        msg = 'SYST:COMM:SER:SEND "VOLT:NPLC {}"'.format(nplc)
        print(msg)
        self.instr.write(msg)

        self.set_voltage_limit(v_limit)
        time.sleep(1)
        self.instr.write('FORMat:ELEMENTS ALL')
        time.sleep(0.5)

        self.instr.write('SOUR:DCON:STARt {}'.format(start))
        self.instr.write('SOUR:DCON:STEP {}'.format(step_size))
        self.instr.write('SOUR:DCON:STOP {}'.format(stop))
        self.instr.write('SOUR:DCON:DELTa {}'.format(delta))

        self.instr.write('SOUR:DCON:DELay 5e-3')
        self.instr.write('SOUR:DCON:CAB ON')  # Enables Compliance Abort
        self.instr.write('TRAC:POIN {}'.format(steps))
        time.sleep(0.2)
        print('Prepare to arm')
        self.instr.write('SOUR:DCON:ARM')
        time.sleep(1)
        print('Init')
        self.instr.write('INIT:IMM', expect_return=True)
        time.sleep(3)
        return True

    def _2182a_comm(self, cmd=None):
        if cmd is None:
            cmd_6220 = 'SYST:COMM:SER:ENT?'
            expect_return = True
        else:
            cmd_6220 = 'SYST:COMM:SER:SEND "{}"'.format(cmd)
            print(cmd_6220)
            expect_return = False

        # # TODO: REFACTOR THESE IF'S!!!!!!!!!!!
        # i = 0
        # if expect_return:
        #     reply = self.instr.query(cmd_6220, delay=0.4).strip()
        #     print('keithley_6220.pyL262: ', repr(reply))
        # else:
        #     self.instr.write(cmd_6220)
        #     reply = ''
        # if expect_return:
        #     while len(reply) < 2:
        #         if i > 10:
        #             print('Trying to get return ', i)
        #         reply = self.instr.query(cmd_6220, delay=0.4).strip()
        #         print('keithley_6220.pyL262: ', repr(reply))
        #         i = i + 1
        #         if i > 50:
        #             print('Reply apparantly never arrives?!?!?')
        #             break

        i = 0
        reply = ''
        if not expect_return:
            self.instr.write(cmd_6220)
        else:
            while len(reply) < 2:
                if i > 10:
                    print('Trying to get return ', i)
                reply = self.instr.query(cmd_6220, delay=0.2)
                print(i, 'keithley_6220.pyL262: ', repr(reply))
                reply = reply.strip()
                i = i + 1
                if i > 50:
                    print('Reply apparantly never arrives?!?!?')
                    break

        if len(reply) > 0:
            while ord(reply[0]) == 19:
                reply = reply[1:]
                if len(reply) == 0:
                    break
        return reply

    def read_2182a_channel_2(self, probe_current):
        print(probe_current)
        self.set_current(probe_current)
        self.set_voltage_limit(1)
        self.output_state(True)
        time.sleep(0.2)

        self._2182a_comm(':CONF:VOLT')
        self._2182a_comm(':SENSE:CHANNEL 2')
        self._2182a_comm(':SAMP:COUNT 1')
        self._2182a_comm(':READ?')
        value_raw = self._2182a_comm()
        self._2182a_comm(':READ?')
        value_raw = self._2182a_comm()
        # print(value_raw)

        # while ord(value_raw[0]) == 19:
        #     value_raw = value_raw[1:]
        print('VALUE RAW!!', value_raw)
        value = float(value_raw)
        time.sleep(0.5)
        # status = self.read_status()
        # print('Status (check for compliance): ', status)
        self.output_state(False)
        return value

    def prepare_delta_measurement(self, probe_current, v_limit=1.0):
        # Set range on nanovoltmeter'
        # self.scpi_comm('SYST:COMM:SER:SEND "VOLT:RANG 0.1"')
        self.instr.write('SYST:COMM:SER:SEND "VOLT:RANG {}"'.format(v_limit))

        # self.scpi_comm('SYST:COMM:SER:SEND ":SENSE:VOLT:CHANNEL1:RANGE:AUTO ON"')
        time.sleep(1)
        # self.scpi_comm('SYST:COMM:SER:SEND "VOLT:RANG?"')
        # print('2181a range: ', self.scpi_comm('SYST:COMM:SER:ENT?'))

        self.instr.write('SYST:COMM:SER:SEND "VOLT:NPLC 5"')
        # print('2181a NPLC: ', self.scpi_comm('SYST:COMM:SER:ENT?'))

        # self.scpi_comm('SYST:COMM:SER:SEND "VOLT:NPLC?"')
        # print('2181a NPLC: ', self.scpi_comm('SYST:COMM:SER:ENT?'))

        # self.reset_device()
        # TODO!!! SET RANGE ON 6221!!!

        time.sleep(3)
        self.instr.write('FORMat:ELEMents READING, TSTAMP')
        self.set_voltage_limit(v_limit)
        # self.scpi_comm(':FORMAT:SREG BIN')
        # print('High', self.scpi_comm('SOURCE:DELTA:HIGH 2e-6'))
        # print('SOURCE:DELTA:HIGH {}'.format(probe_current))
        self.instr.write('SOURCE:DELTA:HIGH {}'.format(probe_current))
        self.instr.write('SOURCE:DELTA:DELAY 100e-3')  # Apparantly strictly needed...

        # self.scpi_comm('SOURCE:DELTA:CAB ON') # Abort on compliance
        time.sleep(3.0)
        print('SOURCE:DELTA:ARM')
        self.instr.write('SOURCE:DELTA:ARM')
        time.sleep(3.0)
        print('INIT:IMM')
        self.instr.write('INIT:IMM')

    def end_delta_measurement(self):
        self.instr.write('SOUR:SWE:ABOR')

    def read_delta_measurement(self):
        reply = self.instr.query('SENS:DATA:FRESH?').strip()
        print('delta reply', reply)
        value_raw, dt_raw = reply.split(',')
        value = float(value_raw)
        dt = float(dt_raw)
        return value, dt

    # def read_differential_conductance_measurement(self):
    #     reply = self.scpi_comm('SENS:DATA:FRESH?').strip()
    #     fields = reply.split(',')
    #     row = {
    #         'reading': float(fields[row_nr + 0][:-3]),
    #         'time': float(fields[row_nr + 1][:-4]),
    #         'current': float(fields[row_nr + 2][:-3]),
    #         'avoltage': float(fields[row_nr + 3][:-3]),
    #         'compliance_ok': fields[row_nr + 4][0] == 'F',
    #         'reading_nr': int(fields[row_nr + 5][1:6]),
    #     }
    #     # print('delta reply', reply)
    #     # value_raw, dt_raw = reply.split(',')
    #     # value = float(value_raw)
    #     # dt = float(dt_raw)
    #     # return value, dt
    #     return row


if __name__ == '__main__':
    SOURCE = Keithley6220(interface='lan', path='192.168.0.3')
    for _ in range(0, 5):
        print(SOURCE.instr.query('*IDN?'))

    print()

    SOURCE._2182a_comm(':STATus:QUEue:NEXT?')
    v_xx_error_queue = SOURCE._2182a_comm()
    SOURCE._2182a_comm(':DATA:FRESh?')
    value_raw = SOURCE._2182a_comm()
    print('Value from 6221: ', value_raw)
    exit()

    SOURCE.source_sine_wave(741, 1.2e-8)
    time.sleep(30)
    exit()

    current = 5e-10

    SOURCE.set_current_range(current)
    SOURCE.set_current(current)
    SOURCE.output_state(True)

    exit()

    # SOURCE.scpi_comm('SYST:COMM:SER:SEND "VOLT:NPLC 10"')
    # SOURCE.scpi_comm('SYST:COMM:SER:SEND "VOLT:NPLC?"')
    # print('2181a NPLC: ', SOURCE.scpi_comm('SYST:COMM:SER:ENT?'))

    SOURCE.prepare_delta_measurement(1e-5)
    # SOURCE.end_delta_measurement()
    # exit()
    t = time.time()
    rows = []
    SOURCE.perform_differential_conductance_measurement(
        start=1e-6, stop=2e-5, step=2e-7, delta=1.0e-7
    )
    print('End peform start')
    for i in range(0, 250):
        data = SOURCE.scpi_comm('SENS:DATA:FRESH?').strip()
        if len(data) > 2:
            fields = data.split(',')
            try:
                row = {
                    'reading': float(fields[0][:-3]),
                    'time': float(fields[1][:-4]),
                    'current': float(fields[2][:-3]),
                    'avoltage': float(fields[3][:-3]),
                    'compliance_ok': fields[4][0] == 'F',
                    'reading_nr': int(fields[5][1:6]),
                }
                print(row)
                rows.append(row)
            except ValueError:
                print('Error in row: {}'.format(data))
        if (i > 15) and (len(data) < 5):
            break
    print('End measurement')
    nvz = SOURCE.scpi_comm('SOUR:DCON:NVZ?').strip()
    print('NVZero', nvz)

    SOURCE.end_delta_measurement()
    print('Number of lines: {}'.format(len(rows)))
    print('First and last line:')
    print(rows[0])
    print(rows[-1])

    # print(SOURCE.read_2182a_channel_2(1e-5))

    # SOURCE.scpi_comm('SYST:COMM:SER:SEND "VOLT:NPLC 10"')
    # SOURCE.end_delta_measurement()
    exit()

    print('Read software version:')
    print(SOURCE.read_software_version())
    print()
    # condition = SOURCE.scpi_comm('STATUS:MEASurement:CONDition?')[::-1]
    # print(condition)
    # exit()

    # for i in range(0, 2):
    # print(SOURCE.perform_delta_measurement())

    # SOURCE._end_delta_measurement()
