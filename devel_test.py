import agilent_34410A as dmm

driver  = dmm.Agilent34410ADriver()

print driver.read()
print driver.clearErrorQueue()