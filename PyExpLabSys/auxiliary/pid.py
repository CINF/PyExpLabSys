class PID():
    
    def __init__(self, pid_p=0.15, pid_i=0.0025, pid_d=0, p_max=54):
        self.setpoint = -9999
        self.pid_p = pid_p
        self.pid_i = pid_i
        self.pid_d = pid_d
        self.p_max = p_max
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
        self.setpoint = setpoint
        return setpoint

    def wanted_power(self, value):
        """ Return the best estimate for wanted power """
        self.error = self.setpoint - value
        power = self.pid_p * self.error
        power = power + self.pid_i * self.int_err
        if (power < self.p_max) and (power > 0):
            self.int_err += self.error
        if power > self.p_max:
            power = self.p_max
        if power < 0:
            power = 0 
        return power
