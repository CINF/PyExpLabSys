import telnetlib
import time

f = telnetlib.Telnet('130.225.87.47', 5025) #Clustersource
#f = telnetlib.Telnet('130.225.87.50', 5025) #Volvo

f.write('*IDN?' + '\n')
s = f.read_until(chr(10),1)
print len(s)
print s[:-1]


f.write('reading = smua.measure.v' + '\n')
f.write('*TRG' + '\n')
s = f.read_until(chr(10),1)
print s[:-1]

f.write('reading = smua.measure.i()' + '\n')
f.write('print(reading)' + '\n')
s = f.read_until(chr(10),1)
print s[:-1]
