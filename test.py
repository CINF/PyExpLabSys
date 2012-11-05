import CPX400DP as CPX
import agilent_34410A as agilent
import time

AgilentDriver = agilent.Agilent34410ADriver()

AgilentDriver.SelectMeasurementFunction('RESISTANCE')

print AgilentDriver.Read()

AgilentDriver.SelectMeasurementFunction('FRESISTANCE')

print AgilentDriver.Read()


AgilentDriver.SelectMeasurementFunction('RESISTANCE')

print AgilentDriver.Read()


CPXdriver  = CPX.CPX400DPDriver(1)

print CPXdriver.SetVoltage(0)

print CPXdriver.ReadCurrentLimit()

print CPXdriver.SetCurrentLimit(1.9)

print CPXdriver.ReadCurrentLimit()

print CPXdriver.OutputStatus(True)

print CPXdriver.ReadActualCurrent()

print CPXdriver.ReadActualVoltage()


