import time
import sys
#sys.path.append('/home/pi/PyExpLabSys')
import PyExpLabSys.drivers.omega_D6400 as omega_D6400


omega = omega_D6400.OmegaD6400(address=1, port='/dev/ttyUSB1')
omega.update_range_and_function(0, action='voltage', fullrange='10')

print omega.read_voltage(0)
for i in range(0,1000):
    print omega.read_voltage(0)
    time.sleep(0.2)
