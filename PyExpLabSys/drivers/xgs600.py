import serial
import time

class XGS600Driver():

    def __init__(self):
        self.f = serial.Serial('/dev/ttyUSB0')

    def xgs_comm(self,command):
        comm = "#00" + command + "\r"

        self.f.write(comm)
        time.sleep(0.25)
        bytes = self.f.inWaiting()
        complete_string = self.f.read(bytes)
        complete_string = complete_string.replace('>','').replace('\r','')
        return(complete_string)


    def read_all_pressures(self):
        pressure_string = self.xgs_comm("0F")
        #print pressure_string
        if len(pressure_string)>0:
            temp_pressure = pressure_string.replace(' ','').split(',')
            pressures = []
            for press in temp_pressure:
                if press == 'OPEN':
                    pressures.append(-1)
                else:
                    try:
                        pressures.append((float)(press))
                    except:
                        pressures.append(-2)
        else:
            pressures = [-3]
        return(pressures)


    def list_all_gauges(self):
        gauge_string = self.xgs_comm("01")
        gauges = ""
        for i in range(0,len(gauge_string),2):
            gauge = gauge_string[i:i+2]
            if gauge == "10":
                gauges = gauges + str(i/2) + ": Hot Filament Gauge\n"
            if gauge == "FE":
                gauges = gauges + str(i/2) + ": Empty Slot\n"
            if gauge == "40":
                gauges = gauges + str(i/2) + ": Convection Board\n"
            if gauge == "3A":
                gauges = gauges + str(i/2) + ": Inverted Magnetron Board\n"
        return(gauges)

    def read_pressure(self, id):
        pressure = self.xgs_comm('02' + id)
        try:
            val = float(pressure)
        except ValueError:
            val = -1.0
        return(val)

    def filament_lit(self, id):
        filament = self.xgs_comm('34' + id) 
        return(int(filament))

    def emission_status(self, id):
        status = self.xgs_comm('32' + id)
        emission = status == '01'
        return emission

    def set_smission_off(self, id):
        self.xgs_comm('30' + id)
        time.sleep(0.1)
        return self.emission_status(id)

    def set_emission_on(self, id, filament):
        if filament == 1:
            command = '31'
        if filament == 2:
            command = '33'
        self.xgs_comm(command + id)
        return self.emission_status(id)

    def read_software_version(self):
        gauge_string = self.xgs_comm("05")
        return(gauge_string)


    def read_pressure_unit(self):
        gauge_string = self.xgs_comm("13")
        unit = gauge_string.replace(' ','')
        if unit == "00":
            unit = "Torr"
        if unit == "01":
            unit = "mBar"
        if unit == "02":
            unit = "Pascal"
        return(unit)


if __name__ == '__main__':
    xgs = XGS600Driver()
    print xgs.read_all_pressures()
    #print xgs.read_pressure_unit()

    xgs.set_emission_on('I1',1)
    time.sleep(0.2)
    print xgs.read_pressure('I1')
    time.sleep(0.2)
    print xgs.emission_status('I1')
    print xgs.read_pressure('I1')

