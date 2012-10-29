class PID():
    
    def __init__(self):
        self.setpoint = -9999
        self.Kp = 0.05
        self.Ki = 0.005
        self.Kd = 0
        self.Pmax = 60
        self.IntErr = 0

    def ResetIntError(self):
        self.IntErr = 0

    def UpdateSetpoint(self,setpoint):
        self.setpoint = setpoint
        return setpoint
        
    def WantedPower(self,T):
        
        error = self.setpoint - T
        
        P = self.Kp * error
        P = P + self.Ki * self.IntErr
        
        if (P<self.Pmax) and (P>0):
            self.IntErr += error

        if P>self.Pmax:
            P = self.Pmax
        if P<0:
            P = 0
            
            
        return P
