""" Reads continuously updated values and decides whether it is time to log a new point 

Three loggers (or checkers) exist: ValueLogger, LoggingCriteriumChecker and
EjlaborateLoggingCriteriumChecker. The internal workings are slightly different, but all
checks the newest measured value against the last recorded value and determines whether
or not the newest value should be saved.
    A timeout counter (default 600s) forces data to be saved at no longer than this
interval.
    An event checker (logarithmic or linear) checks for events based on a large enough
change since the last recorded value.
The amount of data saved using these, can be down to 0.1% to 3% of the full dataset while
retaining key features.

 *LoggingCriteriumChecker* is an object class capable of keeping track of saved values
for several different datasets - each represented by a unique codename. Its checks are
manually handled for every data point in any thread handling the collected data. This
checker is responsible for timestamping the data value.

Example:
--------------------
import time
from PyExpLabSys.common.value_logger import LoggingCriteriumChecker

# Create an instance
logger = LoggingCriteriumChecker(
    codenames=['pressure', 'speed'],
    types=['log', 'lin'],
    criteria=[0.25, 5],
    time_outs=[600, 600],
)
# "Pressure" events are detected at changes of 25% and timeouts of 600s
# "Speed" events are detected at changes of 5 units and timeouts of 600s

# Use in some code
while True:
    for codename in ['pressure', 'speed']:
        data = get_newest_data(codename)
        if logger.check(codename, value): # Data is timestamped in the check
            # Save the data point triggering the event
            save_point(codename, time.time(), value)
--------------------
While it records the event, the details around that event are not recorded and it can be
difficult to say whether the event was a sudden step function or a slow rise over eight
minutes.

 *EjlaborateLoggingCriteriumChecker* deprecates the LoggingCriteriumChecker by expanding
the functionality greatly. Compared to its predecessor, all data points between events
are buffered in the instance. On an event, the buffer is looped through from the newest
measurement to follow the slope down to the beginning and record every data point based
on a subcriterium (default is 10% of the normal criterium). This takes care of most
details around the event. For even finer recording, the remaining buffer is run through
a deviation_check, which checks whether a linear representation of the data deviates
significantly from the average linear representation of data gathered from timeout
events. Any significantly deviant data is added to the save pool. These data points can
be served the timestamp which also makes it possible to use this module as a filter on
existing data.

Example:
--------------------
from PyExpLabSys.common.value_logger import EjlaborateLoggingCriteriumChecker

# Create an instance
logger = EjlaborateLoggingCriteriumChecker(
    codenames=['pressure', 'speed'],
    types=['log', 'lin'],
    criteria=[0.25, 5],
    time_outs=[600, 600],
    grades=[0.1, 0.1],
)
# Pressure events are detected at 25% value change and timeouts of 600s. 2.5% is used as
# the subcriterium. Speed events are detected at 5 unit changes and timeouts of 600s.
# 0.5 units are used as the subcriterium.

# Use in some code
while True:
    for codename in ['pressure', 'speed']:
        time_, value = get_newest_data(codename)
        if logger.check(codename, value, now=time_): # Defaulting 'now' to None will make
                                                     # the logger timestamp the value
            datapoints_to_save = logger.get_data(codename)
            for t, y in datapoints_to_save:
                save_data(codename, (t, y))
--------------------
This means that data can be saved sparsely when no events are occuring, but retain high
resolution around the events.

 *ValueLogger* is a threaded class where each instance continuously monitors a single
value stream (codename) which is served by a Reader class. Other than that, it logs
similarly to the other two checkers. A "model" parameter ("sparse" or "event") chooses
whether it should behave like the original LoggingCriteriumChecker ("sparse") or the new
EjlaborateLoggingCriteriumChecker ("event"). At present, the latter does not include the
deviation checks, though. If needed, it is probably better to use the EjlaborateLogging-
CriteriumChecker instead to keep the ValueLogger (more) lightweight.

Example 1: Using the ValueLogger to monitor pressure and speed
--------------------
import time
import threading
from PyExpLabSys.common.value_logger import ValueLogger

class Reader(threading.Thread)
    def __init__(self, driver):
        super().__init__()
        self.driver = driver
        self.running = False
        self.pressure = 0
        self.speed = 0

    def value(self, channel):
        if channel == 1:
            return self.pressure
        if channel == 2:
            return self.speed

    def run(self):
        self.running = True
        while self.running:
            self.pressure = self.driver.get_pressure()
            self.speed = self.driver.get_speed()
            time.sleep(1)

reader = Reader(pressure_and_speed_driver)
reader.start() # start the run method

loggers = {}
loggers['pressure'] = ValueLogger(
    reader,
    channel=1,
    comp_type='log',
    comp_val=0.25, # 25% value change
    maximumtime=600, # timeout in seconds
    model='event', # get higher res info about the onset of events
    grade=0.1, # default 2.5% value change as subcriterium
)
loggers['speed'] = ValueLogger( # use old behaviour by using the default model
    reader,
    channel=2,
    comp_type='lin',
    comp_val=5, # 5 units value change
    maximumtime=600, # timeout in seconds
)
for codename in ['pressure', 'speed']:
    loggers[codename].start()

# Continue in main thread
time.sleep(3)
while True:
    # New way to do it:
    if loggers['pressure'].read_trigged():
        datapoints = loggers['pressure'].get_data()
        # The logger timestamps the data, when it reads a new value
        for t, y in datapoints:
            my_save_data_function('pressure', (t, y))
    # The old way still works:
    if loggers['speed'].read_trigged():
        # We timestamp the data here, even though it might be several seconds old
        datapoint = (time.time(), loggers['speed'].get_value())
        my_save_data_function('speed', datapoint)
    time.sleep(1)

--------------------
Example 2: Use the ValueLogger to filter an existing dataset
--------------------
import time
from PyExpLabSys.common.value_logger import ValueLogger

# Define a reader to serve the data
class Reader(object):
    def __init__(self, time_array, data_array):
        self.counter = 0
        self.time = time_array
        self.data = data_array
        self.running = True

    def value(self):
        try:
            data = self.data[self.counter]
            self.time_value = self.time[self.counter]
            self.counter += 1
            return data
        except IndexError:
            self.running = False

time_array, value_array = load_my_data(file)

reader = Reader(time_array, value_array) # this one is not threaded

logger = ValueLogger(
    reader,
    comp_type='log',
    comp_val=0.25, # 25 % value change
    maximumtime=600,
    model='event', # use new model
    # skip the sleep time in the logger and have the reader serve the timestamps
    simulate=True,
) # 'channel' defaults to None and 'grade' defaults to 0.1
logger.start()

# Let the filter run through the data
while reader.running:
    time.sleep(1)
    # You could also start getting the data here
    # if logger.read_trigged():
    #    data_so_far = logger.get_data()
    # Code hasn't been checked for possible race conditions in this high paced scenario

# Get filtered data
filtered_datapoints = logger.get_data()
for t, y in filtered_datapoints:
    my_save_data_function('pressure', (t, y))
--------------------
"""

import threading
import time
import numpy as np
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
        simulate=False,
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
            simulate (bool): Simulate how the ValueLogger runs through a non-live data set (i.e.
                the Reader will serve the time stamps).
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
        # Event algorithm
        self.saved_points = []
        self.buffer = []
        if grade >= 1 or grade <= 0:
            raise ValueError('"grade" must be larger than 0 and less than 1')
        self.grade = grade
        self.simulate = simulate
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
        self.saved_points = []
        self.status['trigged'] = False

    def get_data(self):
        """Cleanly return the event based sorted data and clear trigger latch"""
        data = self.saved_points.copy()
        data.sort()
        self.clear_trigged()
        return data

    def run(self):
        error_count = 0

        while not self.status['quit']:
            if not self.simulate:
                time.sleep(1)
            if self.channel is None:
                self.value = self.valuereader.value()
            else:
                self.value = self.valuereader.value(self.channel)
            if self.simulate:
                if self.channel is None:
                    this_time = self.valuereader.time_value
                else:
                    this_time = self.valuereader.time_value[self.channel]
            else:
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
                    # Special case to prevent error codes of 0 to be continuously saved
                    if self.last['val'] == 0:
                        if abs(self.last['val'] - self.value) == 0:
                            val_trigged = False
                error_count = 0
                # Get sign of slope for use in secondary check
                diff = self.value - self.last['val']
                if diff < 0:
                    sign = -1
                elif diff > 0:
                    sign = 1
                else:
                    sign = 0
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
                    self.event_handler((this_time, self.value), sign)
                self.last['time'] = this_time
                self.last['val'] = self.value
                self.saved_points.append((this_time, self.value))
                self.status['trigged'] = True
            elif time_trigged and (self.value is not None):
                self.last['time'] = this_time
                self.last['val'] = self.value
                if self.event_model:
                    self.buffer = []
                self.saved_points.append((this_time, self.value))
                self.status['trigged'] = True
            else:
                if error_count == 0 and self.event_model:
                    self.buffer.append((this_time, self.value))

    def event_handler(self, data_point, sign):
        """This method does the actual assesment of which extra values to save in an
        event. Fine tuning this is most easily done by subclassing and overwriting
        this method. It will loop through the self.buffer attribute and add
        point (x, y) to be saved to self.saved_points attribute."""
        latest = data_point
        saved_points = []
        # Log every point on the up-/down-hill event that has a variation greater than
        # 10% of the general criterium
        crit = (
            self.compare['val']
            * self.compare['grade_val']
        )
        t_0 = self.last['time']
        y_0 = self.last['val']
        for i in range(len(self.buffer) - 1, -1, -1):
            t_i, y_i = self.buffer[i]
            diff = latest[1] - y_i
            if diff * sign < 0:
                # Remaining buffer could be run through an extra deviation check here
                break
            if self.compare['type'] == 'lin':
                if abs(diff) > crit:
                    saved_points.append((t_i, y_i))
                    latest = (t_i, y_i)
            else: # type log
                # Handle zeros in case they are used as error codes
                if y_i == 0:
                    if latest[1] == 0:
                        continue
                    saved_points.append((t_i, y_i))
                    latest = (t_i, y_i)
                if latest[1] == 0:
                    if y_i == 0:
                        continue
                    saved_points.append((t_i, y_i))
                    latest = (t_i, y_i)
                # Not entirely sure why, at this point, the next check does not seem to
                # cause a ZeroDivisionError, but it seems to work
                if (
                    abs(diff) / abs(latest[1]) > crit
                    or abs(y_i - y_0) / abs(y_0) > crit
                ):
                    saved_points.append((t_i, y_i))
                    latest = (t_i, y_i)
        for point in saved_points:
            self.saved_points.append(point)
        self.buffer = []


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
            if last == 0 and abs_diff > 0:
                self.last_time[codename] = time.time()
                self.last_values[codename] = value
                return True
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

        ###
        self.r_time = []
        self.r_value = []
        self.r_buffer = []
        self.extra = {}
        self.extra['time'] = []
        self.extra['value'] = []
        self.means = []
        self.timeout_ref = 0
        self.timeout_counter = 0
        self.deviation_factor = 50
        self.in_timeout = False
        ###
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

    def check(self, codename, value, now=None):
        """Check a new value"""
        try:
            measurement = self.measurements[codename]
        except KeyError:
            raise KeyError('Codename \'{}\' is unknown'.format(codename))

        # Check for time
        if now is None:
            now = time.time()

        # Pull out last value
        last = self.last_values.get(codename)

        # Never trigger if the compared value is None
        if value is None:
            return False

        # Always trigger for the first value
        if last is None:
            self.last_time[codename] = now
            self.last_values[codename] = value
            # data buffer is empty
            self.saved_points[codename].append((now, value))
            return True

        # Always trigger on a timeout
        if now - self.last_time[codename] > measurement['time_out']:
            # Do extra fancy stuff to prevent artificial tailing
            self.timeout_counter += 1
            self.in_timeout = True
            self.timeout_handler(codename, now, value)
            self.in_timeout = False

            self.last_time[codename] = now
            self.last_values[codename] = value

            # reset data buffer and save point(s)
            self.buffer[codename] = []
            self.saved_points[codename].append((now, value))
            return True

        # Check if below lower compare value
        if (
            measurement['low_compare'] is not None
            and value < measurement['low_compare']
        ):
            # self.buffer[codename].append(now, value)
            return False

        # Compare
        diff = value - last
        if diff < 0:
            sign = -1
        elif diff > 0:
            sign = 1
        else:
            sign = 0

        abs_diff = abs(diff)
        if measurement['type'] == 'lin':
            if abs_diff > measurement['criterium']:
                self.event_handler(codename, 'lin', (now, value), sign)
                # Update references before returning true
                self.last_time[codename] = now
                self.last_values[codename] = value
                self.buffer[codename] = []
                self.saved_points[codename].append((now, value))
                return True
        elif measurement['type'] == 'log':
            if last == 0:
                if abs_diff > 0:
                    self.event_handler(codename, 'log', (now, value), sign)
                    # Update references before returning true
                    self.last_time[codename] = now
                    self.last_values[codename] = value
                    self.buffer[codename] = []
                    self.saved_points[codename].append((now, value))
                    return True
                self.buffer[codename].append((now, value))
                return False
            if (abs_diff / abs(last) > measurement['criterium']) or (
                abs(value - self.last_values[codename]) / abs(last)
                > measurement['criterium']
            ):
                self.event_handler(codename, 'log', (now, value), sign)
                # Update references before returning true
                self.last_time[codename] = now
                self.last_values[codename] = value
                self.buffer[codename] = []
                self.saved_points[codename].append((now, value))
                return True
        # Append point to buffer before returning false
        self.buffer[codename].append((now, value))
        return False

    def check_buffer_deviation(self, codename, now, value):
        """Compare the buffer data to the general data variation obtained from timeouts"""
        # Don't check if we haven't yet had a timeout
        if self.timeout_counter == 0:
            return

        # Skip if data set is too small
        if len(self.buffer[codename]) < 10:
            return

        # Get the variation of the data in the buffer
        buff = np.array(self.buffer[codename])
        newest = (now, value)
        oldest = (self.last_time[codename], self.last_values[codename])
        slope = (newest[1] - oldest[1]) / (newest[0] - oldest[0])
        intercept = newest[1] - slope * newest[0]
        fit = intercept + slope * buff[:, 0]

        time_limit = (oldest[0], newest[0])  ##

        smoothed = smooth(buff[:, 1], 5)
        # The following gives a RuntimeWarning on 0's. This is okay for this purpose
        # A way to suppress this is to run np.seterr(invalid='ignore'), but this will
        # seemingly affect the Python master script
        variance = ((fit - smoothed) ** 2) / smoothed  # Division by 0 = np.nan
        mean_var = np.mean(variance)
        if self.in_timeout:
            self.timeout_ref += mean_var
        mean_var = self.timeout_ref / self.timeout_counter  # running mean of variance

        # Find any extra data points with significant deviation
        extra = np.where(variance > mean_var * self.deviation_factor)[0]
        for i in range(len(self.buffer[codename])):  ##
            self.r_value.append(variance[i])  ##
            self.r_time.append(buff[i, 0])  ##
        lextra = len(extra)
        for j, i in enumerate(extra):  ##
            # Skip duplicates and save everything else
            if j > 0 and j < lextra - 1:
                if buff[i, 1] == buff[i - 1, 1] and buff[i, 1] == buff[i + 1, 1]:
                    continue
            self.extra['time'].append(buff[i, 0])  ##
            self.extra['value'].append(buff[i, 1])  ##
            self.saved_points[codename].append(self.buffer[codename][i])
        self.means.append([time_limit, mean_var])  ##

        self.r_buffer.append(self.buffer[codename])  ##
        self.r_buffer.append(newest)  ##

    def event_handler(self, codename, type_, data_point, sign):
        """This method does the actual assesment of which extra values to save in an
        event. Fine tuning this is most easily done by subclassing and overwriting
        this method. It will loop through the self.buffer[codename] attribute and add
        point (x, y) to be saved to self.saved_points[codename] attribute."""
        latest = data_point
        saved_points = []
        # Log every point on the up-/down-hill event that has a variation greater than
        # 10% of the general criterium
        crit = (
            self.measurements[codename]['criterium']
            * self.measurements[codename]['grade']
        )
        t_0 = self.saved_points[codename][0][0]  ###
        y_0 = self.last_values[codename]
        for i in range(len(self.buffer[codename]) - 1, -1, -1):
            t_i, y_i = self.buffer[codename][i]
            diff = latest[1] - y_i
            if diff * sign < 0:
                # Run the remaining buffer through the deviation check
                self.buffer[codename] = self.buffer[codename][:i]
                self.check_buffer_deviation(codename, t_i, y_i)
                break
            if type_ == 'lin':
                if abs(diff) > crit:
                    saved_points.append((t_i, y_i))
                    latest = (t_i, y_i)
            else: # type log
                # Handle zeros in case they are used as error codes
                if y_i == 0:
                    if latest[1] == 0:
                        continue
                    saved_points.append((t_i, y_i))
                    latest = (t_i, y_i)
                if latest[1] == 0:
                    if y_i == 0:
                        continue
                    saved_points.append((t_i, y_i))
                    latest = (t_i, y_i)
                # Not entirely sure why, at this point, the next check does not seem to
                # cause a ZeroDivisionError, but it seems to work
                if (
                    abs(diff) / abs(latest[1]) > crit
                    or abs(y_i - y_0) / abs(y_0) > crit
                ):
                    saved_points.append((t_i, y_i))
                    latest = (t_i, y_i)
        for point in saved_points:
            self.saved_points[codename].append(point)

    def timeout_handler(self, codename, now, value):
        """This method can be overwritten to do something extra on the buffered data
        before saving the point that triggered the timeout. Default here is to run the
        check_buffer_deviation method."""
        self.check_buffer_deviation(codename, now, value)


def smooth(data, width=1):
    """Average `data` with `width` neighbors"""
    if len(data) == 0:
        print('Empty data!')
        return data
    smoothed_data = np.zeros(len(data))
    smoothed_data[width:-width] = data[2 * width :]
    for i in range(2 * width):
        smoothed_data[width:-width] += data[i : -2 * width + i]
        if i < width:
            smoothed_data[i] = sum(data[0 : i + width + 1]) / len(
                data[0 : i + width + 1]
            )
            smoothed_data[-1 - i] = sum(data[-1 - i - width :]) / len(
                data[-1 - i - width :]
            )
    smoothed_data[width:-width] = smoothed_data[width:-width] / (2 * width + 1)
    return smoothed_data
