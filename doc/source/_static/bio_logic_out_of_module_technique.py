"""Example implementation of an out of code Technique"""

from __future__ import print_function

### Out of module technique implementation START

from PyExpLabSys.drivers.bio_logic import Technique, DataField,\
    TechniqueArgument, c_float, E_RANGES, TECHNIQUE_IDENTIFIERS_TO_CLASS


class MyOCV(Technique):  # pylint: disable=too-few-public-methods
    """Open Circuit Voltage (OCV) technique class.

    The OCV technique returns data on fields (in order):

    * time (float)
    * Ewe (float)
    * Ece (float) (only wmp3 series hardware)
    """

    #: Data fields definition
    data_fields = {
        'vmp3': [DataField('Ewe', c_float), DataField('Ece', c_float)],
        'sp300': [DataField('Ewe', c_float)],
    }

    def __init__(self, rest_time_T=10.0, record_every_dE=10.0,
                 record_every_dT=0.1, E_range='KBIO_ERANGE_AUTO'):
        """Initialize the OCV technique

        Args:
            rest_time_t (float): The amount of time to rest (s)
            record_every_dE (float): Record every dE (V)
            record_every_dT  (float): Record evergy dT (s)
            E_range (str): A string describing the E range to use, see the
                :data:`E_RANGES` module variable for possible values
        """
        args = (
            TechniqueArgument('Rest_time_T', 'single', rest_time_T, '>=', 0),
            TechniqueArgument('Record_every_dE', 'single', record_every_dE,
                              '>=', 0),
            TechniqueArgument('Record_every_dT', 'single', record_every_dT,
                              '>=', 0),
            TechniqueArgument('E_Range', E_RANGES, E_range,
                              'in', E_RANGES.values()),
        )
        super(MyOCV, self).__init__(args, 'ocv.ecc')

TECHNIQUE_IDENTIFIERS_TO_CLASS['KBIO_TECHID_OCV'] = MyOCV

### Out of module technique implementation END


from PyExpLabSys.drivers.bio_logic import SP150
import time


def test_myocv_technique():
    """Test the OCV technique"""
    sp150 = SP150('10.54.6.74')
    sp150.connect()
    ocv = MyOCV(rest_time_T=0.2,
              record_every_dE=10.0,
              record_every_dT=0.01)
    sp150.load_technique(0, ocv)
    sp150.start_channel(0)
    try:
        time.sleep(0.1)
        while True:
            data_out = sp150.get_data(0)
            if data_out is None:
                break
            print(data_out.Ewe)
            print(data_out.Ewe_numpy)
            time.sleep(0.1)
    except KeyboardInterrupt:
        sp150.stop_channel(0)
        sp150.disconnect()
    else:
        sp150.stop_channel(0)
        sp150.disconnect()


if __name__ == '__main__':
    test_myocv_technique()
