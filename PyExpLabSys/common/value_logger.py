""" Read a continuously updated values and decides whether it is time to log a new point """

import threading
import time
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

class ValueLogger(threading.Thread):
    """ Reads continuously updated values and decides
    whether it is time to log a new point """
    def __init__(self, value_reader, maximumtime=600, low_comp=None,
                 comp_type='lin', comp_val=1, channel=None):
        threading.Thread.__init__(self)
        self.daemon = True
        self.valuereader = value_reader
        self.value = None
        self.channel = channel
        self.maximumtime = maximumtime
        self.status = {}
        self.compare = {}
        self.last = {}
        self.compare['type'] = comp_type
        self.compare['val'] = comp_val
        self.compare['low_comp'] = low_comp
        self.status['quit'] = False
        self.status['trigged'] = False
        self.last['time'] = 0
        self.last['val'] = 0

    def read_value(self):
        """ Read the current value """
        return self.value

    def read_trigged(self):
        """ Ask if the class is trigged """
        return self.status['trigged']

    def clear_trigged(self):
        """ Clear trigger """
        self.status['trigged'] = False

    def run(self):
        error_count = 0
        while not self.status['quit']:
            time.sleep(1)
            if self.channel is None:
                self.value = self.valuereader.value()
            else:
                self.value = self.valuereader.value(self.channel)
            time_trigged = ((time.time() - self.last['time'])
                            > self.maximumtime)

            try:
                if self.compare['type'] == 'lin':
                    val_trigged = not (self.last['val'] - self.compare['val']
                                       < self.value
                                       < self.last['val'] + self.compare['val'])
                if self.compare['type'] == 'log':
                    val_trigged = not (self.last['val'] *
                                       (1 - self.compare['val'])
                                       < self.value
                                       < self.last['val'] *
                                       (1 + self.compare['val']))
                error_count = 0
            except (UnboundLocalError, TypeError):
                #Happens when value is not yet ready from reader
                val_trigged = False
                time_trigged = False
                error_count = error_count + 1
            if error_count > 15:
                raise Exception('Error in ValueLogger')

            # Will only trig on value if value is larger than low_comp
            if self.compare['low_comp'] is not None:
                if self.value < self.compare['low_comp']:
                    val_trigged = False

            if (time_trigged or val_trigged) and (self.value is not None):
                self.status['trigged'] = True
                self.last['time'] = time.time()
                self.last['val'] = self.value


class LoggingCriteriumChecker(object):
    """Class that performs a logging criterium check and stores last values for a series
    of meaurements

    """

    def __init__(self, codenames=(()), types=(()), criteria=(()), time_outs=None,
                 low_compare_values=None):
        """Initialize the logging criterium checker

        .. note:: If given, codenames, types and criteria must be sequences with the same
            number of elements

        Args:
            codename (sequence): A sequence of codenames
            types (sequence): A sequence of logging criteria types ('lin' or 'log')
            criteria (sequence): A sequence of floats indicating the values change
                that should trigger a log
            time_outs (sequence): An (optional) sequence of floats or integers that
                indicate the logging timeouts in seconds. Defaults to 600.
            low_compare_values (sequence): An (optional) sequence of lower limits under
                which the logging criteri will never trigger
        """
        error_message = None
        if len(types) != len(codenames):
            error_message = 'The must be exactly as many types as codenames'
        if len(criteria) != len(codenames):
            error_message = 'The must be exactly as many criteria as codenames'
        if low_compare_values is not None and len(low_compare_values) != len(codenames):
            error_message = 'If low_compare_values is given, it must contain as many '\
                            'values as there are codenames'
        if time_outs is not None and len(time_outs) != len(codenames):
            error_message = 'If time_outs is given, it must contain as many '\
                            'values as there are codenames'
        if error_message is not None:
            raise ValueError(error_message)

        # Init local variables
        if low_compare_values is None:
            low_compare_values = [None for _ in codenames]
        if time_outs is None:
            time_outs = [600 for _ in codenames]

        self.last_values = {}
        self.last_time = {}
        self.measurements = {}
        for codename, type_, criterium, time_out, low_compare in zip(codenames, types,
                                                                     criteria, time_outs,
                                                                     low_compare_values):
            self.add_measurement(codename, type_, criterium, time_out, low_compare)

    @property
    def codenames(self):
        """Return the codenames"""
        return list(self.measurements.keys())

    def add_measurement(self, codename, type_, criterium, time_out=600, low_compare=None):
        """Add a measurement channel"""
        self.measurements[codename] = {
            'type': type_, 'criterium': criterium, 'low_compare': low_compare,
            'time_out': time_out,
        }
        # Unix timestamp
        self.last_time[codename] = 0

    def check(self, codename, value):
        """Check a new value"""
        try:
            measurement = self.measurements[codename]
        except KeyError:
            raise KeyError('Codename \'{}\' is unknown'.format(codename))

        # Pull out last value
        last = self.last_values.get(codename)

        # Always trigger for the first value
        if last is None:
            self.last_time[codename] = time.time()
            self.last_values[codename] = value
            return True

        # Always trigger on a timeout
        if time.time() - self.last_time[codename] > measurement['time_out']:
            self.last_time[codename] = time.time()
            self.last_values[codename] = value
            return True

        # Check if below lower compare value
        if measurement['low_compare'] is not None and value < measurement['low_compare']:
            return False

        # Compare
        abs_diff = abs(value - last)
        if measurement['type'] == 'lin':
            if abs_diff > measurement['criterium']:
                self.last_time[codename] = time.time()
                self.last_values[codename] = value
                return True
        elif measurement['type'] == 'log':
            if abs_diff / abs(last) > measurement['criterium']:
                self.last_time[codename] = time.time()
                self.last_values[codename] = value
                return True
        return False
