"""Function for power_supply.py
A PID heat ramp experiment has been fitted to a polynomium to be fed back into the power supply."""

def poly_current(x, param):
    # Initialize
    if type(x) == int:
        y = 0.
        x = float(x)
    elif type(x) == float:
        y = 0.
    else:
        y = np.zeros(len(x))

    # Calculate
    for i in range(len(param)):
        y += param[i] * (x**i)

    return y

t_change = 160
t_end = 760
param1 = [1.97412e+00, -5.610136e-02, 4.222524e-03, -7.447891e-05,
          5.8796189e-07, -2.1858488e-09, 3.11700276e-12]
param2 = [3.84551107e+00, 3.13766395e-03, 1.33381151e-05, -8.52580115e-08,
          1.96335874e-10, -2.15923940e-13, 9.58996158e-17]

import json
class FitParameters(object):
    def __init__(self, filename='psu_parameters.fit'):
        self.file = filename
        f = open(filename, 'r')
        self.data = json.load(f)
        f.close()
        self.counter = 0

    def get_setpoint(self, t):
        t_change = self.data['points'][str(self.counter)]
        if t > self.data['duration']:
            return False
        elif t > t_change:
            self.counter += 1
        return(poly_current(t, self.data['fit_vals'][str(self.counter)]))

    def reset(self):
        self.counter = 0
