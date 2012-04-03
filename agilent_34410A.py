import time

def scpi_comm(command):
	#ser = serial.Serial(0)
	#comm = "#00" + command + "\r"

    f = open('/dev/usbtmc0', 'w')
    f.write(command)
    f.close()

    time.sleep(0.01)
    return_string = ""    
    if command[-1]=='?':
        a = ' '
        f = open('/dev/usbtmc0', 'r')
        while not (ord(a) == 10):
            a = f.read(1)
            return_string += a
        f.close()
    return return_string
    


def readSoftwareVersion():
	version_string = scpi_comm("*IDN?")
	return(version_string)

def resetDevice():
	scpi_comm("*RST")
	return(True)

def deviceClear():
	scpi_comm("*abort")
	return(True)

def read():
    value = scpi_comm("READ?")
    return value
    

print read()
#deviceClear()
#resetDevice()
#readSoftwareVersion()
