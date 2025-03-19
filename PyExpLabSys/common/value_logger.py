""" Reads continuously updated values and decides whether it is time to log a new point """

import threading
import time
from PyExpLabSys.common.supported_versions import python2_and_3

python2_and_3(__file__)


class ValueLogger(threading.Thread):
    """Reads continuously updated values and decides
    whether it is time to log a new point"""

    def __init__(
        self,
        value_reader,
        maximumtime=600,
        low_comp=None,
        comp_type='lin',
        comp_val=1,
        channel=None,
        model='sparse',
        grade=0.1,
    ):
        """Initialize the value logger

        Args:
            value_reader (instance): Instance of a Reader class (should be defined somewhere FIXME)
            maximumtime (float): Timeout in seconds
            low_comp (float): Optional low limit beneath which readings should be disregarded
            comp_type (str): Comparison type either 'lin' or 'log' for linear or
                logarithmic criteria, respectively
            comp_val (float): Trigger value for the comparison
            channel (int): Optional channel for data input from Reader class
            model (str): Model behaviour of value logger 'sparse' or 'event'.
                'sparse' value logger (default) behaves like normal as in it will trigger
                on data points where the newly given point deviates by more than comp_val
                since the last trigger and then returns True.
                'event' will use the sparse value logger as an event trigger, buffering
                all data between events and then sort through the data based on a subcriterium
            grade (0 < float < 1): The subcriterium used for the event based data sorting.
                The subcriterium will be comp_val * grade. Default is 10%.
        """
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
        # "Fancy" event algorithm
        self.saved_points = []
        self.buffer = []
        if grade >= 1 or grade <= 0:
            raise ValueError('"grade" must be larger than 0 and less than 1')
        self.grade = grade
        if model == 'sparse':
            self.event_model = False
        elif model == 'event':
            self.event_model = True
            self.compare['grade_val'] = grade * comp_val
        else:
            raise ValueError('"model" must be either "sparse" or "event"')

    def read_value(self):
        """Read the current value"""
        return self.value

    def read_trigged(self):
        """Ask if the class is trigged"""
        return self.status['trigged']

    def clear_trigged(self):
        """Clear trigger"""
        self.status['trigged'] = False

    def get_data(self):
        """Cleanly return the event based sorted data and clear trigger latch"""
        data = self.saved_points.copy()
        data.sort()
        self.saved_points = []
        self.clear_trigged()
        return data

    def run(self):
        error_count = 0

        while not self.status['quit']:
            time.sleep(1)
            if self.channel is None:
                self.value = self.valuereader.value()
            else:
                self.value = self.valuereader.value(self.channel)
            this_time = time.time()
            time_trigged = (this_time - self.last['time']) > self.maximumtime

            try:
                if self.compare['type'] == 'lin':
                    val_trigged = not (
                        self.last['val'] - self.compare['val']
                        < self.value
                        < self.last['val'] + self.compare['val']
                    )
                if self.compare['type'] == 'log':
                    val_trigged = not (
                        self.last['val'] * (1 - self.compare['val'])
                        < self.value
                        < self.last['val'] * (1 + self.compare['val'])
                    )
                error_count = 0
            except (UnboundLocalError, TypeError):
                # Happens when value is not yet ready from reader
                val_trigged = False
                time_trigged = False
                error_count = error_count + 1
            if error_count > 15:
                raise Exception('Error in ValueLogger')

            # Will only trig on value if value is larger than low_comp
            if self.compare['low_comp'] is not None:
                if self.value < self.compare['low_comp']:
                    val_trigged = False

            if val_trigged and (self.value is not None):
                if self.event_model:
                    # Loop back through previous data points to find onset
                    last = {'time': this_time, 'val': self.value}
                    for i in range(len(self.buffer) - 1, -1, -1):
                        t_i, y_i = self.buffer[i]
                        if self.compare['type'] == 'lin':
                            low_val_trigged = not (
                                last['val'] - self.compare['grade_val']
                                < y_i
                                < last['val'] + self.compare['grade_val']
                            )
                        if self.compare['type'] == 'log':
                            low_val_trigged = not (
                                last['val'] * (1 - self.compare['grade_val'])
                                < y_i
                                < last['val'] * (1 + self.compare['grade_val'])
                            )
                        if low_val_trigged:
                            # Save extra point
                            self.saved_points.append((t_i, y_i))
                            last = {'time': t_i, 'val': y_i}
                    self.saved_points.append((self.last['time'], self.last['val']))
                    self.buffer = []
                self.last['time'] = this_time
                self.last['val'] = self.value
                self.status['trigged'] = True
            elif time_trigged and (self.value is not None):
                self.status['trigged'] = True
                self.last['time'] = this_time
                self.last['val'] = self.value
                if self.event_model:
                    self.saved_points.append((this_time, self.value))
                    self.buffer = []
            else:
                if self.event_model:
                    self.buffer.append((this_time, self.value))


class LoggingCriteriumChecker(object):
    """Class that performs a logging criterium check and stores last values for a series
    of meaurements

    """

    def __init__(
        self,
        codenames=(()),
        types=(()),
        criteria=(()),
        time_outs=None,
        low_compare_values=None,
    ):
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
                which the logging criteria will never trigger
        """
        error_message = None
        if len(types) != len(codenames):
            error_message = 'There must be exactly as many types as codenames'
        if len(criteria) != len(codenames):
            error_message = 'There must be exactly as many criteria as codenames'
        if low_compare_values is not None and len(low_compare_values) != len(codenames):
            error_message = (
                'If low_compare_values is given, it must contain as many '
                'values as there are codenames'
            )
        if time_outs is not None and len(time_outs) != len(codenames):
            error_message = (
                'If time_outs is given, it must contain as many '
                'values as there are codenames'
            )
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
        for codename, type_, criterium, time_out, low_compare in zip(
            codenames, types, criteria, time_outs, low_compare_values
        ):
            self.add_measurement(codename, type_, criterium, time_out, low_compare)

    @property
    def codenames(self):
        """Return the codenames"""
        return list(self.measurements.keys())

    def add_measurement(
        self, codename, type_, criterium, time_out=600, low_compare=None
    ):
        """Add a measurement channel"""
        self.measurements[codename] = {
            'type': type_,
            'criterium': criterium,
            'low_compare': low_compare,
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

        # Never trigger if the compared value is None
        if value is None:
            return False

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
        if (
            measurement['low_compare'] is not None
            and value < measurement['low_compare']
        ):
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


class EjlaborateLoggingCriteriumChecker(object):
    """Class that performs a logging criterium check and stores last values for a series
    of meaurements

    Compared to the standard LoggingCriteriumChecker that just checks last saved value against
    the newest measure value, this Ejlaborate version buffers all values since last save (or check?).
    If more than 10% of the timeout time has passed and it would return true, cycle backwards
    through the buffered data and choose select few datapoints representing the change leading
    up to the criterium check.
    """

    def __init__(
        self,
        codenames=(()),
        types=(()),
        criteria=(()),
        time_outs=None,
        low_compare_values=None,
        grades=None,
    ):
        """Initialize the logging criterium checker

        .. note:: If given, codenames, types, criteria and grades must be sequences with
            the same number of elements

        Args:
            codename (sequence): A sequence of codenames
            types (sequence): A sequence of logging criteria types ('lin' or 'log')
            criteria (sequence): A sequence of floats indicating the values change
                that should trigger a log
            time_outs (sequence): An (optional) sequence of floats or integers that
                indicate the logging timeouts in seconds. Defaults to 600.
            low_compare_values (sequence): An (optional) sequence of lower limits under
                which the logging criteria will never trigger
            grades (sequence): An (optional) sequence of subcriteria (0-100%) to use
                in the event handling condition. Defaults to 10%
        """
        error_message = None
        if len(types) != len(codenames):
            error_message = 'There must be exactly as many types as codenames'
        if len(criteria) != len(codenames):
            error_message = 'There must be exactly as many criteria as codenames'
        if low_compare_values is not None and len(low_compare_values) != len(codenames):
            error_message = (
                'If low_compare_values is given, it must contain as many '
                'values as there are codenames'
            )
        if time_outs is not None and len(time_outs) != len(codenames):
            error_message = (
                'If time_outs is given, it must contain as many '
                'values as there are codenames'
            )
        if grades is not None and len(grades) != len(codenames):
            error_message = (
                'If grades is given, it must contain as many '
                'values as there are codenames'
            )
        if grades is not None and error_message is None:
            for grade in grades:
                if grade <= 0 or grade >= 1:
                    error_message = 'If grades is given, each grade must be larger than 0 and less than 1'
        if error_message is not None:
            raise ValueError(error_message)

        # Init local variables
        if low_compare_values is None:
            low_compare_values = [None for _ in codenames]
        if time_outs is None:
            time_outs = [600 for _ in codenames]
        if grades is None:
            grades = [0.1 for _ in codenames]

        self.last_values = {}
        self.last_time = {}
        self.measurements = {}
        self.buffer = {}
        self.saved_points = {}
        for codename, type_, criterium, time_out, low_compare, grade in zip(
            codenames, types, criteria, time_outs, low_compare_values, grades
        ):
            self.add_measurement(
                codename, type_, criterium, time_out, low_compare, grade
            )

    @property
    def codenames(self):
        """Return the codenames"""
        return list(self.measurements.keys())

    def add_measurement(
        self, codename, type_, criterium, time_out=600, low_compare=None, grade=0.1
    ):
        """Add a measurement channel"""
        if not type_ in ['lin', 'log']:
            raise ValueError('Type must be either "lin" or "log"')
        self.measurements[codename] = {
            'type': type_,
            'criterium': criterium,
            'low_compare': low_compare,
            'time_out': time_out,
            'grade': grade,
        }
        self.buffer[codename] = []
        self.saved_points[codename] = []
        # Unix timestamp
        self.last_time[codename] = 0

    def get_data(self, codename):
        """Return the data saved during checks and reset list"""
        data = self.saved_points[codename].copy()
        data.sort()
        self.saved_points[codename] = []
        return data

    def check(self, codename, value, time_=time.time()):
        """Check a new value"""
        try:
            measurement = self.measurements[codename]
        except KeyError:
            raise KeyError('Codename \'{}\' is unknown'.format(codename))

        # Pull out last value
        last = self.last_values.get(codename)

        # Never trigger if the compared value is None
        if value is None:
            return False

        # Always trigger for the first value
        if last is None:
            self.last_time[codename] = time_
            self.last_values[codename] = value
            # data buffer is empty
            self.saved_points[codename].append((time_, value))
            return True

        # Always trigger on a timeout
        if time_ - self.last_time[codename] > measurement['time_out']:
            self.last_time[codename] = time_
            self.last_values[codename] = value
            # reset data buffer
            self.buffer[codename] = []
            self.saved_points[codename].append((time_, value))
            return True

        # Check if below lower compare value
        if (
            measurement['low_compare'] is not None
            and value < measurement['low_compare']
        ):
            return False

        # Compare
        abs_diff = abs(value - last)
        if measurement['type'] == 'lin':
            if abs_diff > measurement['criterium']:
                self.event_handler(codename, 'lin', (time_, value))
                # Update references before returning true
                self.last_time[codename] = time_
                self.last_values[codename] = value
                self.buffer[codename] = []
                self.saved_points[codename].append((time_, value))
                return True
        elif measurement['type'] == 'log':
            if abs_diff / abs(last) > measurement['criterium']:
                self.event_handler(codename, 'log', (time_, value))
                # Update references before returning true
                self.last_time[codename] = time_
                self.last_values[codename] = value
                self.buffer[codename] = []
                self.saved_points[codename].append((time_, value))
                return True
        # Append point to buffer before returning false
        self.buffer[codename].append((time_, value))
        return False

    def event_handler(self, codename, type_, data_point):
        """This method does the actual assesment of which extra values to save in an
        event. Fine tuning this is most easily done by subclassing and overwriting
        this method. It will loop through the self.buffer[codename] attribute and add
        point (x, y) to be saved to self.saved_points[codename] attribute."""
        latest = data_point
        saved_points = []
        # Log every point with a "sequential" variation of 10% (of general criterium)
        crit = (
            self.measurements[codename]['criterium']
            * self.measurements[codename]['grade']
        )
        for i in range(len(self.buffer[codename]) - 1, -1, -1):
            t_i, y_i = self.buffer[codename][i]
            if type_ == 'lin':
                if abs(latest[1] - y_i) > crit:
                    saved_points.append((t_i, y_i))
                    latest = (t_i, y_i)
            else:
                if abs(latest[1] - y_i) / abs(latest[1]) > crit:
                    saved_points.append((t_i, y_i))
                    latest = (t_i, y_i)
        for point in saved_points:
            self.saved_points[codename].append(point)
