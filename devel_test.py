import CPX400DP as CPX
import time

driver  = CPX.CPX400DPDriver(1)

print "1"
print driver.ReadSetVoltage()
print driver.ReadCurrentLimit()
print driver.ReadSoftwareVersion()
print driver.ReadCurrentLimit()
print driver.ReadSetVoltage()
print driver.OutputStatus(False)
print "2"

