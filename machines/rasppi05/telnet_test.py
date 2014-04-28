import telnetlib
import time

tn = telnetlib.Telnet('agilent-34972a',5025)

tn.write('CONFIGURE?' + '\n')

response = tn.read_until(chr(10),5)

print response
