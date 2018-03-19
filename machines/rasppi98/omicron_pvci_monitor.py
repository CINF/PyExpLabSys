"""Measure values from omicron's two PVCi's (ion gauge controllers), log to database and set on live socket server"""

from __future__ import print_function

from PyExpLabSys.common.sockets import LiveSocket, DateDataPullSocket
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.value_logger import LoggingCriteriumChecker
from PyExpLabSys.common.utilities import get_logger
from PyExpLabSys.drivers import epimax
from time import sleep

import credentials

# Wait time in seconds between serial communications
WAIT = 0.25

# codename : (address, key)
CODENAME_TRANSLATION = {
    'omicron_ana_pressure': (2, 'ion_gauge_1_pressure'),
    'omicron_prep_pressure': (1, 'ion_gauge_1_pressure'),
    'omicron_roughing_2_prep': (1, 'slot_a_value_1'),
    'omicron_roughing_1_ana': (2, 'slot_a_value_1'),
    'omicron_roughing_3_diff': (2, 'slot_b_value_1'),
    }

EXTRA_LIVE = {
    }
LOG = get_logger('pvci_monitor', level='info')

def print_values(values):
    """Print values (type: dict) in a nice fashion to terminal window"""
    print('-'*20)
    for codename, value in values.items():
        print(codename + ': {} mbar'.format(value))

def run(pvci, live_socket, pullsocket, database_saver, criterium_checker):
    """Measure and log """
    
    values = {}
    for codename in CODENAME_TRANSLATION.keys():
        values[codename] = 0

    # Main loop
    while True:
        for codename, (address, key) in CODENAME_TRANSLATION.items():
            sleep(WAIT)
            pvci.address = address
            value = pvci.get_field(key)
            values[codename] = value
            LOG.debug("Measure %s, (%s, %s) value %s", codename, address, key, value)
            live_socket.set_point_now(codename, value)
            pullsocket.set_point_now(codename, value)
            if criterium_checker.check(codename, value):
                LOG.debug('TRIG')
                database_saver.save_point_now(codename, value)
            print_values(values)
            


#epimax.minimalmodbus.TIMEOUT=1
def main():
    """Main function """
    pvci = epimax.PVCi('/dev/serial/by-id/'
                       'usb-FTDI_USB-RS485_Cable_FT0N0UFX-if00-port0',
                       slave_address = 1)

    # Start live socket
    live_socket = LiveSocket(
        'omicron_pvci',
        list(CODENAME_TRANSLATION.keys()),
        )
    live_socket.start()

    # Start pull socket
    pullsocket = DateDataPullSocket('omicron_pvci_pull',
                                    list(CODENAME_TRANSLATION.keys()),
                                    timeouts = 2.5,
                                    )
    pullsocket.start()
        
    # Start database saver
    database_saver = ContinuousDataSaver(
        'dateplots_omicron', credentials.USERNAME,
        credentials.PASSWORD, list(CODENAME_TRANSLATION.keys()),
        )
    database_saver.start()

    # Criterium checker
    criterium_checker = LoggingCriteriumChecker(
        codenames=list(CODENAME_TRANSLATION.keys()),
        types=['log']*len(CODENAME_TRANSLATION.keys()),
        criteria=[0.05]*len(CODENAME_TRANSLATION.keys()),
        time_outs=[300]*len(CODENAME_TRANSLATION.keys()),
        )

    # Main loop
    try:
        run(pvci, live_socket, pullsocket, database_saver, criterium_checker)
    except KeyboardInterrupt:
        sleep(WAIT)
        pvci.close()
        live_socket.stop()
        pullsocket.stop()
        database_saver.stop()
    except:
        LOG.exception("Omicron pvci data logger stopped")

if __name__ == '__main__':
    main()
