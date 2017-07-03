# pylint: disable=R0913,W0142,C0103 

import sys
sys.path.insert(1, '/home/pi/PyExpLabSys')
import time
import PyExpLabSys.common.valve_control as valve_control
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket

valve_names = [0] * 20
for i in range(0, 20):
    valve_names[i] = str(i + 1)
Pullsocket = DateDataPullSocket('sniffer valvecontrol',
                                valve_names, timeouts=[2]*20)
Pullsocket.start()

Pushsocket = DataPushSocket('sniffer valvecontrol',
                            action='enqueue')
Pushsocket.start()

vc = valve_control.ValveControl(valve_names, Pullsocket, Pushsocket)
vc.start()

while True:
    time.sleep(1)

vc.running = False
