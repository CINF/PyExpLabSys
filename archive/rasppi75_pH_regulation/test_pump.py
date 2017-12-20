
from __future__ import print_function

import time
from PyExpLabSys.drivers.wpi_al1000 import AL1000


for baud in [19200]:#(300, 9600, 19200):
    print(baud)
    al1000 = AL1000(
        port="/dev/serial/by-id/usb-FTDI_USB-RS232_Cable_FTV9X9TM-if00-port0",
        baudrate=baud,
    )
    print(al1000.set_vol(1))
    print(al1000.set_rate(10))
    print(al1000.start_program())
    al1000.stop_program()
    #print(repr(al1000.get_firmware()))
#    while True:
#        print(al1000._send_command("VER"))
    
