from SCPI import SCPI
import time
    
class Agilent34972ADriver(SCPI):

    def __init__(self, method='lan', address=''):
        if method == 'file':
            SCPI.__init__(self, address, 'file')
        if method == 'lan':
            SCPI.__init__(self, address, 'lan')

    def read_single_scan(self):
        self.scpi_comm("TRIG:SOURCE TIMER")
        self.scpi_comm("TRIG:COUNT 1")
        self.scpi_comm("INIT")
        time.sleep(0.1)
        status = int(self.scpi_comm("STATUS:OPERATION:CONDITION?"))
        status_bin = bin(status)[2:].zfill(16)
        while status_bin[11] == '1':
            status = int(self.scpi_comm("STATUS:OPERATION:CONDITION?"))
            status_bin = bin(status)[2:].zfill(16)
            time.sleep(0.5)
        response = self.scpi_comm("FETCH?")
        response = response.split(',')
        return_values = []
        for val in response:
            return_values.append(float(val))
        return(return_values)

    def abort_scan(self):
        self.scpi_comm("ABOR")

    def read_configuration(self):
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
            conf_string += str(channel) + "\n" + "Measurement type: " + conf[3*i] + "\nRange: " + conf[3*i+1] + "\nResolution: " + conf[3*i + 2] + "\nNPLC: " + str(float(nplc_conf[i])) + "\n \n"
            i += 1
        return(conf_string)

    def set_scan_interval(self,interval):
        self.scpi_comm("TRIG:TIMER  " + str(interval))

    def set_integration_time(self,channel,nplc):
        comm_string = "VOLT:DC:NPLC  " + str(nplc) + ",(@" + str(channel) + ")"
        self.scpi_comm(comm_string)

    def read_scan_interval(self):
        response = self.scpi_comm("TRIG:TIMER?")
        print response

    def read_scan_list(self):
        response = self.scpi_comm("ROUT:SCAN?")
        response = response.strip()
        start = response.find('@')
        response =  response[start+1:-1]
        return(response.split(','))

    def set_scan_list(self,channels):
        comm = "ROUT:SCAN (@"
        for chn in channels:
            comm += str(chn) + ','
        comm = comm[:-1]
        comm += ")"
        self.scpi_comm(comm)
        return(True)



if __name__ == "__main__":

    scan_list = [101,102,103,104,105,106]

    driver = Agilent34972ADriver()
    driver.set_scan_list(scan_list)
        
    #driver = driver.ResetDevice()
    print driver.read_scan_list()
    #driver.set_integration_time(106,20)
    print driver.read_configuration()

    #print driver.read_scan_list()
    print driver.read_single_scan()

    #driver.read_scan()

