""" Driver class for Agilent 34410A DMM """
from __future__ import print_function
import logging
from PyExpLabSys.drivers.scpi import SCPI
import sys
from PyExpLabSys.common.supported_versions import python2_and_3
# Configure logger as library logger and set supported python versions
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
python2_and_3(__file__)


class Agilent34410ADriver(SCPI):
    """ Driver for Agilent 34410A DMM """
    def __init__(self, interface='lan', hostname='', connection_string=''):
        if interface == 'lan': # the LAN interface
            SCPI.__init__(self, interface=interface, hostname=hostname, line_ending='\n')
        if interface == 'file': # For distributions that mounts usbtmc as a file (eg. ubuntu)
            SCPI.__init__(self, interface=interface, device='/dev/usbtmc0')
        if interface == 'usbtmc': # For python-usbtmc (preferred over file)
            SCPI.__init__(self, interface=interface, visa_string=connection_string)

    def config_current_measurement(self):
        """ Configures the instrument to measure current. """
        # FIXME: Take parameter to also be able to select AC
        self.scpi_comm("CONFIGURE:CURRENT:DC")
        return True

    def config_resistance_measurement(self):
        """ Configures the instrument to measure resistance. """
        # FIXME: Take parameter to also be able to select 4W
        self.scpi_comm("CONFIGURE:RESISTANCE")
        return True

    def select_measurement_function(self, function):
        """ Select a measurement function.

        Keyword arguments:
        Function -- A string stating the wanted measurement function.

        """

        values = ['CAPACITANCE', 'CONTINUITY', 'CURRENT', 'DIODE', 'FREQUENCY',
                  'RESISTANCE', 'FRESISTANCE', 'TEMPERATURE', 'VOLTAGE']
        return_value = False
        if function in values:
            return_value = True
            function_string = "FUNCTION " + "\"" + function + "\""
            self.scpi_comm(function_string)
        return return_value

    def read_configuration(self):
        """ Read device configuration """
        response = self.scpi_comm("CONFIGURE?")
        response = response.replace(' ', ',')
        conf = response.split(',')
        conf_string = ""
        conf_string += "Measurement type: " + conf[0] + "\n"
        conf_string += "Range: " + conf[1] + "\n"
        conf_string += "Resolution: " + conf[2]
        return conf_string

    def set_auto_input_z(self, auto=False):
        """ Change internal resitance """
        if auto:
            self.scpi_comm("VOLT:IMP:AUTO ON")
        else:
            self.scpi_comm("VOLT:IMP:AUTO OFF")

    def read(self):
        """ Read a value from the device """
        value = float(self.scpi_comm("READ?"))
        return value

def main():
    """ Main function """
    if len(sys.argv) == 3:
        interface = sys.argv[1]
        device = sys.argv[2]
        driver = Agilent34410ADriver(interface, hostname=device, connection_string=device)
        print(driver.read())
        driver.select_measurement_function('VOLTAGE')
        print(driver.read())
        driver.select_measurement_function('FRESISTANCE')
        print(driver.read())
    else:
        print('Please provide interface and connection information')
    
if __name__ == "__main__":
    main()
