"""Measure values from thetaprobe PVCi, log to database and set on live socket server"""

from __future__ import print_function


from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.value_logger import LoggingCriteriumChecker
from PyExpLabSys.common.utilities import get_logger
from PyExpLabSys.drivers.epimax import PVCi

import credentials



CODENAME_TRANSLATION = {
    'thetaprobe_main_chamber_pressure': 'ion_gauge_1_pressure',
    'thetaprobe_load_lock_roughing_pressure': 'slot_a_value_1',
    'thetaprobe_main_chamber_temperature': 'slot_b_value_1',
}
EXTRA_LIVE = {
    'thetaprobe_bakeout_setpoint': ('bake_out_setpoint',),
    'thetaprobe_bakeout_remaining': ('remaining_bake_out_time',),
    'thetaprobe_ion_gauge_settings': ('ion_gauge_1_status', 'ion_gauge_emission_setting'),
    }
LOG = get_logger('pvci_monitor', level='debug')



def run(pvci, live_socket, database_saver, criterium_checker):
    """Measure and log"""
    extra_live_value_cache = {key: None for key in EXTRA_LIVE}
    while True:
        values = pvci.get_fields('common')
        LOG.debug('Measured %s', values)
        for codename, value_name in CODENAME_TRANSLATION.items():
            value = values[value_name]
            live_socket.set_point_now(codename, value)
            if criterium_checker.check(codename, value):
                database_saver.save_point_now(codename, value)
                LOG.debug('Saved value %s for codename \'%s\'', value, codename)
        for codename, keys in EXTRA_LIVE.items():
            value = pvci.get_field(keys[0])
            LOG.debug('EXTRA ' + codename + str(value))
            for key in keys[1:]:
                value = value[key]
            if codename == 'thetaprobe_ion_gauge_settings':
                value = value['emission'] + '(' + value['mode'] + ')'
            if codename == 'thetaprobe_bakeout_remaining':
                if pvci.get_field('bakeout_flags')['status_flags'] == ['off']:
                    value = 'Bakeout off'
                else:
                    value = '{:.1f} hour(s)'.format(value)
            if value != extra_live_value_cache[codename]:
                live_socket.set_point_now(codename, value)
                extra_live_value_cache[codename] = value
                LOG.debug('SEND ' + codename + str(value))
    print(values)


def main():
    """Main function"""
    pvci = PVCi('/dev/serial/by-id/'
                'usb-FTDI_USB-RS485_Cable_FTY3M2GN-if00-port0')

    # Start live socket
    live_socket = LiveSocket(
        'thetaprobe_pvci',
        list(CODENAME_TRANSLATION.keys()) + list(EXTRA_LIVE.keys()),
    )
    live_socket.start()

    # Start database saver
    database_saver = ContinuousDataSaver(
        'dateplots_thetaprobe', credentials.USERNAME,
        credentials.PASSWORD, list(CODENAME_TRANSLATION.keys())
    )
    database_saver.start()

    # Set up criterium checker
    criterium_checker = LoggingCriteriumChecker(
        codenames=list(CODENAME_TRANSLATION.keys()),
        types=['log', 'log', 'lin'],
        criteria=[0.1, 0.1, 1.0],
    )


    try:
        run(pvci, live_socket, database_saver, criterium_checker)
    except KeyboardInterrupt:
        pvci.close()
        live_socket.stop()
        database_saver.stop()

main()
