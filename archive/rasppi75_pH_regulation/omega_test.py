
#from omegabus import OmegaBus
#obus = OmegaBus("/dev/serial/by-id/usb-FTDI_USB-RS232_Cable_FTWZCGSW-if00-port0")
#value = obus.read_value(1)
#print(type(value), value)

from PyExpLabSys.drivers.omegabus import OmegaBus
obus = OmegaBus("/dev/serial/by-id/usb-FTDI_USB-RS232_Cable_FTWZCGSW-if00-port0", baud=9600)
value = obus.read_value(1)

def current_to_ph(value):
    """Convert current in milliamps between 4 and 20 to Ph between 0 and 14"""
    slope = 14/16
    ph = (value - 4) * slope
    return ph

value = current_to_ph(value)
print(type(value), value)
