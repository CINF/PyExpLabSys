from scpi import SCPI


class Agilent34410ADriver(SCPI):

    def __init__(self, device, port='lan'):
        SCPI.__init__(self, device, port)

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
        return(return_value)

    def read_configuration(self):
        response = self.scpi_comm("CONFIGURE?")
        response = response.replace(' ', ',')
        conf = response.split(',')
        conf_string = ""
        conf_string += "Measurement type: " + conf[0] + "\n"
        conf_string += "Range: " + conf[1] + "\n"
        conf_string += "Resolution: " + conf[2]
        return(conf_string)

    def set_auto_input_z(self, auto=False):
        if auto:
            self.scpi_comm("VOLT:IMP:AUTO ON")
        else:
            self.scpi_comm("VOLT:IMP:AUTO OFF")

    def read(self):
        value = float(self.scpi_comm("READ?"))
        return value


if __name__ == "__main__":
    driver = Agilent34410ADriver()
    print driver.read()
