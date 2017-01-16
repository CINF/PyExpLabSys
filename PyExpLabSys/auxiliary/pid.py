""" PID calculator """
import logging
from PyExpLabSys.common.supported_versions import python2_and_3
# Configure logger as library logger and set supported python versions
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
python2_and_3(__file__)

class PID(object):
    """ PID calculator """
    def __init__(self, pid_p=0.15, pid_i=0.0025, pid_d=0, p_max=54, p_min=0):
        LOGGER.debug('Starting PID')
        self.setpoint = -9999
        self.pid_p = pid_p
        self.pid_i = pid_i
        self.pid_d = pid_d
        self.p_max = p_max
        self.p_min = p_min
        self.error = 0
        self.int_err = 0

    def integration_contribution(self):
        """ Return the contribution from the i-term """
        return self.pid_i * self.int_err

    def proportional_contribution(self):
        """ Return the contribution from the p-term """
        return self.pid_p * self.error

    def integrated_error(self):
        """ Return the currently integrated error """
        return self.int_err

    def reset_int_error(self):
        """ Reset the integration error """
        self.int_err = 0

    def update_setpoint(self, setpoint):
        """ Update the setpoint """
        LOGGER.debug('Setting setpoint to: ' + str(setpoint))
        self.setpoint = setpoint
        return setpoint

    def wanted_power(self, value):
        """ Return the best estimate for wanted power """
        self.error = self.setpoint - value
        power = self.pid_p * self.error
        power = power + self.pid_i * self.int_err
        if (power < self.p_max) and (power > self.p_min):
            self.int_err += self.error
        elif power > self.p_max:
            power = self.p_max
        elif power < self.p_min:
            power = self.p_min
        return power
