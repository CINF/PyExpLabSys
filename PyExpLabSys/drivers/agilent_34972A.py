""" Driver class for Agilent 34972A multiplexer """
from __future__ import print_function
from PyExpLabSys.drivers.scpi import SCPI
import time
    
class Agilent34972ADriver(SCPI):
    """ Driver for Agilent 34972A multiplexer """
    def __init__(self, name='microreactor-agilent-34972a'):
        #SCPI.__init__(self,'/dev/usbtmc1','file')
        SCPI.__init__(self, interface='lan', hostname=name)

    def read_single_scan(self):
        """ Read a single scan-line """
        self.scpi_comm("TRIG:SOURCE TIMER")
        self.scpi_comm("TRIG:COUNT 1")
        self.scpi_comm("INIT")
        time.sleep(0.1)
        status = int(self.scpi_comm("STATUS:OPERATION:CONDITION?"))
        status_bin = bin(status)[2:].zfill(16)
        while status_bin[11] == '1':
            status = int(self.scpi_comm("STATUS:OPERATION:CONDITION?"))
            status_bin = bin(status)[2:].zfill(16)
            time.sleep(0.1)
        response = self.scpi_comm("FETCH?")
        response = response.split(',')
        return_values = []
        for val in response:
            return_values.append(float(val))
        return(return_values)

    def abort_scan(self):
        """ Abort the scan """
        self.scpi_comm("ABOR")

    def read_configuration(self):
        """ Read device configuration """
        scan_list = self.read_scan_list()

        response = self.scpi_comm("CONFIGURE?")
        response = response.replace(' ',',')
        response = response.replace('\"','')
        response = response.replace('\n','')
        conf = response.split(',')

        response = self.scpi_comm("VOLT:DC:NPLC?")
        nplc_conf = response.split(',')

        i = 0
        conf_string = ""
        for channel in scan_list:
            conf_string += str(channel) + "\n" + "Measurement type: "
            conf_string += conf[3*i] + "\nRange: " + conf[3*i+1]
            conf_string += "\nResolution: " + conf[3*i + 2] + "\nNPLC: "
            conf_string += str(float(nplc_conf[i])) + "\n \n"
            i += 1
        return conf_string

    def set_scan_interval(self,interval):
        self.scpi_comm("TRIG:TIMER  " + str(interval))

    def set_integration_time(self,channel,nplc):
        comm_string = "VOLT:DC:NPLC  " + str(nplc) + ",(@" + str(channel) + ")"
        self.scpi_comm(comm_string)

    def read_scan_interval(self):
        response = self.scpi_comm("TRIG:TIMER?")
        print(response)

    def read_scan_list(self):
        """ Return the scan list """
        response = self.scpi_comm("ROUT:SCAN?")
        response = response.strip()
        start = response.find('@')
        response =  response[start+1:-1]
        return response.split(',')

    def set_scan_list(self,channels):
        """ Set the scan list """
        comm = "ROUT:SCAN (@"
        for chn in channels:
            comm += str(chn) + ','
        comm = comm[:-1]
        comm += ")"
        self.scpi_comm(comm)
        return(True)



if __name__ == "__main__":

    driver = Agilent34972ADriver()
    #driver = driver.ResetDevice()
    print(driver.read_scan_list())
    #driver.set_integration_time(106,20)
    print(driver.read_configuration())

    #print driver.read_scan_list()
    print(driver.read_single_scan())

    #driver.read_scan()

