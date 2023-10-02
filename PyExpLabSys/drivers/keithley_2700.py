""" Simple driver for Keithley Model 2700 """
from PyExpLabSys.drivers.scpi import SCPI


class Keithley2700(SCPI):
    """ Simple driver for Keithley Model 2700 """

    def __init__(self, interface, device=None, gpib_address=None):
        if interface == 'serial':
            SCPI.__init__(self, interface='serial', device=device, baudrate=9600)
            self.scpi_comm('FORMAT:ELEMENTS READ')  # Set short read-format
        if interface == 'gpib':
            SCPI.__init__(self, interface=interface, gpib_address=gpib_address)

    def select_measurement_function(self, function):
        """Select a measurement function.

        Keyword arguments:
        Function -- A string stating the wanted measurement function.

        """

        values = [
            'CAPACITANCE',
            'CONTINUITY',
            'CURRENT',
            'DIODE',
            'FREQUENCY',
            'RESISTANCE',
            'FRESISTANCE',
            'TEMPERATURE',
            'VOLTAGE',
        ]
        return_value = False
        if function in values:
            return_value = True
            function_string = "FUNCTION " + "\"" + function + "\""
            self.scpi_comm(function_string)
        return return_value

    def read(self):
        """ Read a value from the device """
        value_raw = self.scpi_comm("READ?").split(',')
        value = float(value_raw[0][0:15])
        timestamp = float(value_raw[1][0:10])
        readings = int(value_raw[2][0:7])
        return value, timestamp, readings


if __name__ == '__main__':
    GPIB = 5
    MUX = Keithley2700(interface='gpib', gpib_address=GPIB)

    print(MUX.scpi_comm('ROUTE:SCAN?'))
    MUX.select_measurement_function('VOLTAGE')
    print(MUX.read())
