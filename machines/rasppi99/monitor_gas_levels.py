
"""Monitor gas levels for B307 gas yard"""

from time import sleep, time
from collections import defaultdict
from pprint import pprint

from PyExpLabSys.drivers.dataq_binary import DI1110
from PyExpLabSys.combos import LiveContinuousLogger
from PyExpLabSys.common.utilities import get_logger
from PyExpLabSys.common.supported_versions import python3_only

# Note, this file makes use of Python 3 division rules, so it cannot be run on Python 2
# without modification
python3_only(__file__)

# Setup logger
LOG = get_logger('gas_levels307', level='debug')
LOG.info('start')


CODENAMES = {
    # The position in the lists corresponds to data cards channel position
    'atex': [
        'gassupply_307_ch4_right',
        'gassupply_307_ch4_left',
        'gassupply_307_h2_right',
        'gassupply_307_h2_left',
        'gassupply_307_CO_left',
        'gassupply_307_CO_right',
    ],
    'regular': [
        'gassupply_307_Ar_right',
        'gassupply_307_Ar_left',
        'gassupply_307_O2_right',
        'gassupply_307_O2_left',
        'gassupply_307_N2_right',
        'gassupply_307_N2_left',
        'gassupply_307_He_right',
        'gassupply_307_He_left',
    ],
}
CODENAMES_LIST = CODENAMES['atex'] + CODENAMES['regular']
SHUNT = {'atex': 25, 'regular': 250}
FULLRANGE = 250


def setup():
    """Initialize combo logger and drivers"""
    # Initialize the combo and start it
    LOG.info('Init LiveContinuousLogger combo')
    combo = LiveContinuousLogger(
        name='gassupply307',
        codenames=CODENAMES['atex'] + CODENAMES['regular'],
        continuous_data_table='dateplots_gassupply',
        username='gassupply',
        password='gassupply',
        time_criteria=900,
        absolute_criteria=0.5,
    )
    combo.start()

    # Init data cards
    LOG.info("Init data card for atex gauges")
    atex = DI1110("/dev/serial/by-id/usb-DATAQ_Instruments_Generic_Bulk_"
                  "Device_599C324B_DI-1110-if00-port0")
    LOG.info('Atex datacard info: %s', atex.info())
    atex.scan_list([0, 1, 2, 3, 4, 5])
    atex.sample_rate(1333)
    atex.packet_size(128)
    LOG.info("Init data card for regular gauges")
    regular = DI1110("/dev/serial/by-id/usb-DATAQ_Instruments_Generic_Bulk_"
                     "Device_599C32F1_DI-1110-if00-port0")
    LOG.info('Regular datacard info: %s', regular.info())
    regular.scan_list([0, 1, 2, 3, 4, 5, 6, 7])
    regular.sample_rate(1000)
    regular.packet_size(128)

    # Start and pack up
    LOG.info('Start daq measurements')
    atex.start()
    regular.start()
    sleep(0.1)
    atex.read()
    regular.read()
    daqs = {'atex': atex, 'regular': regular}

    return daqs, combo


def measure(daqs, combo):
    """Measure loop"""
    data_collect = defaultdict(list)
    start = time()
    # Average the returned measurements over time
    while time() - start < 60:
        for daq_name in ('atex', 'regular'):
            values = daqs[daq_name].read()
            for channel, value_dict in enumerate(values):
                if value_dict is None:
                    continue
                codename = CODENAMES[daq_name][channel]
                # Calculate 4 to 20 mA current signal
                current = value_dict['value'] / SHUNT[daq_name]
                # Calculate pressure, as fraction of current signal range times full range
                pressure = (current - 0.004) / 0.016 * FULLRANGE
                data_collect[codename].append(pressure)
        sleep(0.15)

    # Replace the collected lists of data with their mean and add one, because the gauges
    # measures relative to ambient
    data = {k: sum(v)/len(v) + 1 for k, v in data_collect.items()}
    
    # Send in data
    combo.log_batch_now(data)
    LOG.debug("Data: %s", data)    


def main():
    """Main function"""
    # Get components
    daqs, combo = setup()

    # Run measure in a loop
    try:
        while True:
            measure(daqs, combo)
    except KeyboardInterrupt:
        LOG.info('keyboard interrupt, shutting down')
        LOG.info('stop daqs')
        for daq in daqs.values():
            daq.stop()
        LOG.info('stop LiveContinuousLogger combo')
        combo.stop()
    except:
        LOG.exception('Unhandled exception, bummer')
        raise


if __name__ == '__main__':
    main()
