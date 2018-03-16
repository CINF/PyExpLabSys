""" Calculates temperatures for an RTD """
from __future__ import print_function
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)


class RtdCalculator(object):
    """ Calculates temperatures for an RTD
    The class calculates the RTD temperature at 0C and then
    solves this equation for T, with T0 being 0:
    R = R0(1 + A(T-T0) + B(T-T0)^2) =>
    R = R0(1 + AT + BT**2) =>
    R0BT**2 + R0AT + R0-R = 0
    """
    def __init__(self, calib_temperature, calib_resistance, material='Pt'):
        if material == 'Pt':
            self.coeff_a = 3.9803e-3
            self.coeff_b = -5.775e-7
        if material == 'Mo':
            self.coeff_a = 4.579e-3
            self.coeff_b = 0 # Not correct
        if material == 'W':
            self.coeff_a = 4.403e-3
            self.coeff_b = 0 # Not correct

        self.calib_temperature = calib_temperature
        self.calib_resistance = calib_resistance
        self.resistance_at_0 = calib_resistance / (1 + self.coeff_a * calib_temperature +
                                                   self.coeff_b * calib_temperature**2)


    def find_r(self, temperature):
        """ Find the resistance for a given temperature """
        resistance = self.resistance_at_0 * (1 + self.coeff_a * temperature +
                                             self.coeff_b * temperature**2)
        return resistance

    def find_temperature(self, resistance):
        """ Find the current temperature for given resistance """
        A = self.coeff_a # pylint: disable=invalid-name
        B = self.coeff_b # pylint: disable=invalid-name
        R = resistance # pylint: disable=invalid-name
        R0 = self.resistance_at_0 # pylint: disable=invalid-name

        if B > 0:
            temperature = ((-1 * R0 * A + ((R0 * A)**2 - 4 * R0 * B * (R0 - R))**(0.5)) /
                           (2 * R0 * B))
        else:
            temperature = (R/R0 - 1)/A
        return temperature

if __name__ == '__main__':
    RTD = RtdCalculator(150, 157)
    print(RTD.resistance_at_0)
    print(RTD.find_temperature(100))
