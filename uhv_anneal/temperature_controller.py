import time
import ParallelPortBinaryOut
import socket

class PID:
	#Discrete PID control
		
	def __init__(self, P=2.0, I=0.0, D=1.0, Derivator=0, Integrator=0, Integrator_max=500, Integrator_min=-500):

		self.Kp=P
		self.Ki=I
		self.Kd=D
		self.Derivator=Derivator
		self.Integrator=Integrator
		self.Integrator_max=Integrator_max
		self.Integrator_min=Integrator_min

		self.set_point=0.0
		self.error=0.0

	def update(self,current_value):
		#Calculate PID output value for given reference input and feedback
		
		self.error = self.set_point - current_value

		self.P_value = self.Kp * self.error
		self.D_value = self.Kd * (self.error - self.Derivator)
		self.Derivator = self.error

		self.Integrator = self.Integrator + self.error

		if self.Integrator > self.Integrator_max:
			self.Integrator = self.Integrator_max
		elif self.Integrator < self.Integrator_min:
			self.Integrator = self.Integrator_min

		self.I_value = self.Integrator * self.Ki

		PID = self.P_value + self.I_value + self.D_value

		return PID

	def setPoint(self,set_point):
		#Initilize the setpoint of PID
		
		self.set_point = set_point
		self.Integrator=0
		self.Derivator=0

	def setIntegrator(self, Integrator):
		self.Integrator = Integrator

	def setDerivator(self, Derivator):
		self.Derivator = Derivator

	def setKp(self,P):
		self.Kp=P

	def setKi(self,I):
		self.Ki=I

	def setKd(self,D):
		self.Kd=D

	def getPoint(self):
		return self.set_point

	def getError(self):
		return self.error

	def getIntegrator(self):
		return self.Integrator

	def getDerivator(self):
		return self.Derivator


def read_value(keyword):
    HOST, PORT = "127.0.0.1", 9999
    data = "read_" + keyword
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(data + "\n", (HOST, PORT))
    received = sock.recv(1024)
    temp = float(received)
    return temp

def control_temperature(setpoint):
    while True:
        temperature_outside = read_value("temperature_outside")
        temperature_1 = read_value("temperature_1")
        temperature_2 = read_value("temperature_2")
        print "Temperature outside: " + str(temperature_outside)
        print "Temperature 1: " + str(temperature_1)
        print "Temperature 2: " + str(temperature_2)
        if temperature_1 < setpoint:
            parallel.setState(0,True)
            time.sleep(5)
        else:
            parallel.setState(0,False)
            time.sleep(5)


if __name__ == "__main__":
   parallel = ParallelPortBinaryOut.ParallelPortBinaryOut()
   #parallel.setState(0,False)
   control_temperature(300)
   
   #p=PID(3.0,0.4,1.2) # P, I, D
   #p.setPoint(300)    # Temperature
   #while True:
   #	temperature_outside = read_value("temperature_outside")
   #    temperature_1 = read_value("temperature_1")
   #    temperature_2 = read_value("temperature_2")	
   #	pid = p.update(temperature_1)
