""" Valve controll for VHP-setup """
import time
import PyExpLabSys.common.valve_control as valve_control
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

def main():
    """ Main function """
    valve_names = [0] * 20
    for i in range(0, 20):
        valve_names[i] = str(i + 1)

    pullsocket = DateDataPullSocket('VHP Valvecontrol', valve_names, timeouts=[2]*20)
    pullsocket.start()

    pushsocket = DataPushSocket('VHP calve control', action='enqueue')
    pushsocket.start()

    valve_controller = valve_control.ValveControl(valve_names, pullsocket, pushsocket)
    valve_controller.start()

    while True:
        time.sleep(1)

    valve_controller.running = False

if __name__ == '__main__':
    main()
