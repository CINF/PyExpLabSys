""" Simple driver for Keithley SMU """
from __future__ import print_function
import time
import logging
from PyExpLabSys.drivers.scpi import SCPI
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

class KeithleySMU(SCPI):
    """ Simple driver for Keithley SMU """

    def __init__(self, interface, hostname='', device='', baudrate=9600):
        if interface == 'serial':
            SCPI.__init__(self, interface=interface, device=device,
                          baudrate=baudrate, line_ending='\n')
            self.comm_dev.timeout = 2
            self.comm_dev.rtscts = False
            self.comm_dev.xonxoff = False
            print(self.comm_dev)

        if interface == 'lan':
            SCPI.__init__(self, interface=interface, hostname=hostname)
        self.channel_names = {1: 'a', 2: 'b'}

    def output_state(self, output_on=False, channel=1):
        """ Turn the output on or off """
        if output_on is True:
            self.scpi_comm('smu' + self.channel_names[channel] + '.source.output = 1')
        else:
            self.scpi_comm('smu' + self.channel_names[channel] + '.source.output = 0')
        return output_on

    def set_current_measure_range(self, current_range=None, channel=1):
        """ Set the current measurement range """
        ch_name = 'smu' + self.channel_names[channel] + '.'
        if current_range is None:
            self.scpi_comm(ch_name + 'measure.autorangei = ' + ch_name + 'AUTORANGE_ON')
        else:
            self.scpi_comm(ch_name + 'measure.rangei = ' + str(current_range))
        return True

    def set_integration_time(self, nplc=None, channel=1):
        """ Set the measurement integration time """
        ch_name = 'smu' + self.channel_names[channel] + '.'
        if nplc is None:
            self.scpi_comm(ch_name + 'measure.nplc = 1')
        else:
            self.scpi_comm(ch_name + 'measure.nplc = ' + str(nplc))
        return True

    def read_current(self, channel=1):
        """ Read the measured current """
        self.scpi_comm('reading = smu' + self.channel_names[channel] + '.measure.i()')
        self.scpi_comm('*TRG')
        current_string = self.scpi_comm('print(reading)', True)
        try:
            current = float(current_string)
        except (ValueError, TypeError):
            current = None
            logging.error('Current string: ' + str(current_string))
        return current

    def read_voltage(self, channel=1):
        """ Read the measured voltage """
        self.scpi_comm('reading = smu' + self.channel_names[channel] + '.measure.v()')
        self.scpi_comm('*TRG')
        voltage_string = self.scpi_comm('print(reading)', True)
        try:
            voltage = float(voltage_string)
        except (ValueError, TypeError):
            voltage = None
            logging.error('Voltage string: ' + str(voltage_string))
        return voltage

    def set_source_function(self, function, channel=1):
        scpi_string = ('smu' +  self.channel_names[channel] + '.source.func = ' +
                       self.channel_names[channel] + '.OUTPUT_')
        if function in ('i', 'I'):
            self.scpi_comm(scpi_string + 'DC_AMPS')
            print('Source function: Current')
        if function in ('v', 'V'):
            print('Source function: Voltage')    
            self.scpi_comm(scpi_string + 'DC_VOLTS')

    def set_current_limit(self, current, channel=1):
        """ Set the desired current limit """
        self.scpi_comm('smu' + self.channel_names[channel] +
                       '.source.limiti = ' + str(current))

    def set_voltage(self, voltage, channel=1):
        """ Set the desired voltage """
        self.scpi_comm('smu' + self.channel_names[channel] +
                       '.source.levelv = ' + str(voltage))

    def set_voltage_limit(self, voltage, channel=1):
        """ Set the desired voltate limit """
        self.scpi_comm('smu' + self.channel_names[channel] +
                       '.source.limitv = ' + str(voltage))

    def set_current(self, current, channel=1):
        """ Set the desired current """
        self.scpi_comm('smu' + self.channel_names[channel] +
                       '.source.leveli = ' + str(current))

    def iv_scan(self, v_from, v_to, steps, settle_time, channel=1):
        """ Perform iv_scan """
        ch_name = 'smu' + self.channel_names[channel]
        self.scpi_comm('SweepVLinMeasureI('+ ch_name + ', ' +
                       str(v_from) + ', ' +
                       str(v_to) + ', ' +
                       str(settle_time) + ', ' +
                       str(steps) + ')')
        readings = (self.scpi_comm('printbuffer(1, ' + str(steps) + ', ' + ch_name +
                                   '.nvbuffer1.readings)', True))
        sourcevalues = (self.scpi_comm('printbuffer(1, ' + str(steps) + ', ' + ch_name +
                                       '.nvbuffer1.sourcevalues)', True))
        readings = readings.split(',')
        sourcevalues = sourcevalues.split(',')
        for i in range(0, steps):
            readings[i] = float(readings[i])
            sourcevalues[i] = float(sourcevalues[i])
        return (sourcevalues, readings)

if __name__ == '__main__':
    PORT = '/dev/ttyUSB0'
    SMU = KeithleySMU(interface='serial', device=PORT, baudrate=4800)
    print(SMU.comm_dev.inWaiting())
    SMU.comm_dev.read(SMU.comm_dev.inWaiting())

    print(SMU.read_current(2))
    print(SMU.read_voltage(1))
    print(SMU.read_software_version())

    #print(SMU)
    #SMU.set_source_function('i')
    #SMU.output_state(True)
    #time.sleep(1)
    #SMU.set_voltage(0.00)
    #time.sleep(1)
    #print(SMU.set_voltage_limit(1))
    #time.sleep(1)
    #SMU.set_current(0.0)
    #time.sleep(3)
    #print('Voltage: ' + str(SMU.read_voltage()))
    #print('Current: ' + str(SMU.read_current()))
    #print('-')
    #time.sleep(1)
    #SMU.output_state(False)

    #print(SMU.read_software_version())
    #print('-')
    #print(SMU.read_current())
    #print('-')
    #print(SMU.read_voltage())
    #print('-')
    #print(SMU.iv_scan(v_from=-1.1, v_to=0, steps=10, settle_time=0))

