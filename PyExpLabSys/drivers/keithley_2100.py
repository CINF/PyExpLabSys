"""
Simple driver for Keithley 2100 DMM
"""
from PyExpLabSys.drivers.keithley_2000 import Keithley2000


class Keithley2100(Keithley2000):
    """Simple driver for Keithley 2100 DMM"""

    def __init__(
            self, interface, hostname='', device='', baudrate=9600,
            gpib_address=None, visa_string=None
    ):
        # super().__init__(  # Find out why this does not work...
        Keithley2000.__init__(
            self,
            interface=interface,
            device=device,
            baudrate=baudrate,
            visa_string=visa_string,
            line_ending='\n',
        )


if __name__ == '__main__':
    visa_string = 'USB::0x05E6::0x2100::INSTR'
    DMM = Keithley2100(interface='usbtmc', visa_string=visa_string)

    # print(DMM.comm_dev.read())
    
    print(DMM.read_software_version())
    print(DMM.read_dc_voltage())
