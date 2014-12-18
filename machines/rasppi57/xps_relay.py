# pylint: disable=R0913,W0142,C0103
import time
#from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.drivers.agilent_34972A import Agilent34972ADriver as mux

Pushsocket = DataPushSocket('Tower, energy control', action='store_last')
Pushsocket.start()

agilent = mux('10.54.6.140')

while True:
    time.sleep(0.5)
    try:
        voltage = str(Pushsocket.last[1]['energy'])
        string = "SOURCE:VOLT " + voltage + ", (@205)"
        agilent.scpi_comm(string)
        print(string)
    except TypeError:
        pass

