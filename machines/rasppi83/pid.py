""" PID calculator """
import logging
import time
from PyExpLabSys.common.supported_versions import python2_and_3
# Configure logger as library logger and set supported python versions
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
python2_and_3(__file__)

class PID(object):
    """ PID calculator """
    def __init__(self, pid_p=0.15, pid_i=0.0025, pid_d=0):
        LOGGER.debug('Starting PID')
        # Setpoint
        self.setpoint = -9999
        # PID parameters
        self.pid_p = pid_p
        self.pid_i = pid_i
        self.pid_d = pid_d
        # Error info
        self.last_error = (0, 0)
        self.error = (0, 0)
        self.int_error = 0

    def integration_contribution(self):
        """ Return the contribution from the i-term """
        return self.pid_i * self.int_error

    def proportional_contribution(self):
        """ Return the contribution from the p-term """
        return self.pid_p * self.error[1]

    def differential_contribution(self):
        """ Return the contribution from the d-term """
        return self.pid_d * (self.error[1] - self.last_error[1])/(self.error[0] - self.last_error[1])

    def integrated_error(self):
        """ Return the currently integrated error """
        return self.int_error

    def reset_int_error(self):
        """ Reset the integration error """
        self.int_error = 0

    def reset(self):
        """ Reset errors """
        self.last_error = (time.time(), 0)
        self.error = (time.time(), 0)
        self.int_error = 0

    def get_output(self, value, setpoint):
        """ Return output of PID loop """
        self.last_error = self.error
        self.error = (time.time(), setpoint - value)
        self.int_error += self.error[1]
        return self.proportional_contribution() + self.integration_contribution() - self.differential_contribution()
