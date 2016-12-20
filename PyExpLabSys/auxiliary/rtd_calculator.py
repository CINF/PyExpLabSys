from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)


class RTD_Calculator():

    def __init__(self, Trt, Rrt, material='Pt'):
        if material == 'Pt':
            self.A = 3.9803e-3
            self.B = -5.775e-7
        if material == 'Mo':
            self.A = 4.579e-3
            self.B = 0#Not correct
        if material == 'W':
            self.A = 4.403e-3
            self.B = 0#Not correct

        self.Trt = Trt
        self.Rrt = Rrt
        self.R0 = self.find_r0(Trt,Rrt)
        
    def find_r(self, R0, T):
        A = self.A
        B = self.B
        R = R0(1 + A*T + B*T**2)
        return R
    
    def find_r0(self, Trt, Rrt):
        A = self.A
        B = self.B
        R0 = Rrt/(1 + A*Trt + B*Trt**2)
        return R0
    
    def find_temperature(self, R):
        A = self.A
        B = self.B
        R0 = self.R0

        if B>0: #Check this calculation, dividing by B must be bad nummerics!!
            T = (-1*R0*A + ((R0*A)**2 - 4*R0*B*(R0-R))**(0.5)) / (2*R0*B);
        else:
            T = (R/R0 - 1)/A
        return T
