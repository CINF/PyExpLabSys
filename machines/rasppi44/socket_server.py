""" Valve control for microreactorNG """
import time
import PyExpLabSys.common.valve_control as valve_control
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
#from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)
import credentials


def main():
    """ Main function """
    valve_names = [0] * 20
    codenames = []
    for i in range(1, 21):
        valve_names[i-1] = str(i)
        codenames.append('microreactorng_valve_'+str(i))

    try: # Python 3
        name = chr(0x03BC)
    except ValueError:  # Python 2
        name = unichr(0x03BC) # pylint: disable=undefined-variable

    pullsocket = DateDataPullSocket(name + '-reacorNG valve control',
                                    valve_names, timeouts=[2]*20)
    pullsocket.start()

    pushsocket = DataPushSocket(name + '-reactorNG valve control',
                                action='enqueue')
    pushsocket.start()
    
    
    db_saver = ContinuousDataSaver(
        continuous_data_table='dateplots_microreactorNG',
        username=credentials.username,
        password=credentials.password,
        measurement_codenames = codenames,
    )
    db_saver.start()

    valve_controller = valve_control.ValveControl(valve_names, pullsocket, pushsocket, db_saver, codenames)
    valve_controller.start()

    while True:
        time.sleep(1)

    valve_controller.running = False

if __name__ == '__main__':
    main()
