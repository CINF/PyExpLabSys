import serial
import time

class QMG422():

    def __init__(self):
        self.f = serial.Serial('/dev/ttyUSB0',19200)

    def comm(self,command,multiple=False):

        a = chr(0)
        ok_string = ""
        self.f.write(command + ' \r')
        while a != chr(6):
            self.f.write(command + ' \r')
            a = self.f.read(1)
            #print ord(a)

        ok_string = a

        """
        if ok_string[0] != chr(6):
            self.f.write(command + ' \r')
            a = chr(0)
            ok_string = ""
            while a != chr(10):
                a = self.f.read(1)
                #print ord(a)
                ok_string += a
        """
        ret_string = "Error  " #If this is not overwritten, an error occured
        if ok_string[0] == chr(6):
            ret_string = ""
            a = chr(0)
            while a!=chr(6):
                time.sleep(0.3)
                print "Test 1"
                print ord(a)
                self.f.write(chr(5) + ' \r') #Ask for answer from QMG
                while (ord(a)==13) or (ord(a)==10) or (ord(a)==0): #Skip initial whitespaces and line feeds
                    print "Test 3"
                    time.sleep(0.3)
                    a = self.f.read(1)

            ret_string = ""
            while ord(a) != 13:
                a = self.f.read(1)
                ret_string +=a
        print ret_string
        return ret_string[:-1] #The last character is CR

    #Returns the communication mode
    def communication_mode(self,computer_control=False):
        if computer_control:
            ret_string = self.comm('CMO ,1')
        else:
            ret_string = self.comm('CMO')
        comm_mode = ret_string

        if ret_string == '0':
            comm_mode = 'Console Keybord'
        if ret_string == '1':
            comm_mode = 'ASCII'
        if ret_string == '2':
            comm_mode = 'BIN'
        if ret_string == '3':
            comm_mode = 'Modem'
        if ret_string == '4':
            comm_mode = 'LAN'
        return comm_mode


    def emission_status(self,current=-1,turn_off=False,turn_on=False):
        if current>-1:
            ret_string = self.comm('EMI ,' + str(current))
        else:
            ret_string = self.comm('EMI')
        emission_current = float(ret_string)

        if turn_off ^ turn_on:
            if turn_off:
                self.comm('FIE ,0')
            if turn_on:
                self.comm('FIE ,1')
        ret_string = self.comm('FIE')
        filament_on = ret_string == '1'
        return emission_current,filament_on


    def sem_status(self,voltage=-1,turn_off=False,turn_on=False):
        if voltage>-1:
            ret_string = self.comm('SHV ,' + str(voltage))
        else:
            ret_string = self.comm('SHV')
        print "SEM_STATUS: " + ret_string
        sem_voltage = int(ret_string)


        if turn_off ^ turn_on: #Only accept self-consistent sem-changes
            if turn_off:
                self.comm('SEM ,0')
            if turn_on:
                self.comm('SEM ,1')
        ret_string = self.comm('SEM')
        sem_on = ret_string == "1"
        
        return sem_voltage, sem_on

    def read_voltages(self):
        print "V01: " + self.comm('VO1') #0..150,   1V steps
        print "V02: " + self.comm('VO2') #0..125,   0.5V steps
        print "V03: " + self.comm('VO3') #-30..30,  0.25V steps
        print "V04: " + self.comm('VO4') #0..60,    0.25V steps
        print "V05: " + self.comm('VO5') #0..450,   2V steps
        print "V06: " + self.comm('VO6') #0..450,   2V steps
        print "V07: " + self.comm('VO7') #0..250,   1V steps
        print "V08: " + self.comm('VO8') #-125..125,1V steps 
        print "V09: " + self.comm('VO9') #0..60    ,0.25V steps



    def scan_test(self):
        print "Steps: " + self.comm('MST ,0')
        print "Speed: " + self.comm('MSD ,7')
        print "Auto range:  " + self.comm('AMO, 2')  #Auto range electromter
        print "Scan width  : " + self.comm('MWI, 2')
        print "Mass-scan:   " + self.comm('MMO, 1')  #Mass scan
        #print "Mass-scan:   " + self.comm('MMO, 2')  #Measure whole number masses
        #print "Mass-scan:   " + self.comm('MMO, 5')  #Magic mass-scan
        print "Resolution:  " + self.comm('MRE ,10')   #Resolution
        print "First mass:  " + self.comm('MFM, 17') #First mass, M0
        print "Average:     " + self.comm('MAV ,1')  #Average
        print "--"
        print "Measuring: " + self.comm('CRU')

        start = time.time()
        self.comm('CRU ,1') #Start measurement
        running = self.comm('CRU')
        print running
        while  running == '1':
            running = self.comm('CRU')
            #print running
            #print self.comm('MDB')
            print self.comm('MBH')
            print time.time() - start
            time.sleep(0.5)

        header = self.comm('MBH')
        print header
        header = header.split(',')
        print header[3]
        output_string = ""

        start = time.time()
        for i in range(0,int(header[3])):
            output_string += self.comm('MDB',multiple=True) + '\n'
        print time.time() - start
        print output_string
        """
        datfile = open('ms.dat','w')
        datfile.write(output_string)
        datfile.close()
        print time.time() - start
        """


    def measure_single_mass(self):
        print "Channel: " + self.comm('SMC')
        print "State: " + self.comm('AST')
        print "Dector: " + self.comm('DTY')
        print "Dector: " + self.comm('SDT')
        print "Ion Source " + self.comm('SIT')
        print "SEM: " + self.comm('DSE ,0')
        print "Single mass: " + self.comm('MMO, 3')
        print "Mass number: " + self.comm('MFM, 18') 
        print "Dwell time " +  self.comm('MFM, 12')
        print "Resolution:  " + self.comm('MRE ,20')   #Resolution
        self.comm('CRU ,1') #Start measurement
        start = time.time()
        running = self.comm('CRU')
        print running
        while  running == '1':
            running = self.comm('CRU')
            #print running
            #print self.comm('MDB')
            print self.comm('MBH')
            print time.time() - start
            time.sleep(0.5)
        print "Result: " + self.comm('MDB')
        print self.comm('MBH')


    def qms_status(self):
        ret_string = self.comm('ESQ')
        n = ret_string.find(',')

        sn = int(ret_string[0:n]) #status_number
        st = "" #Status txt

        st += 'Cycle ' + ('Run' if (sn % 2) == 1 else 'Halt')
        sn = sn/2
        st = st + '\n' + ('Multi' if (sn % 2) == 1 else 'Mono')
        sn = sn/2
        st = st + '\n' + 'Emission ' + ('on' if (sn % 2) == 1 else 'off')
        sn = sn/2
        st += '\nSEM ' + ('on' if (sn % 2) == 1 else 'off')
        sn = sn/2
        #The rest of the status bits is not currently used
        return st

if __name__ == "__main__":
    qmg = QMG422()
    #print qmg.communication_mode()
    #print qmg.qms_status()
    #print qmg.sem_status(voltage=1800,turn_on=True)
    #print qmg.emission_status(current=0.8,turn_on=True)
    #print qmg.qms_status()
    print "---"
    qmg.read_voltages()
    #print qmg.scan_test()
    #print qmg.measure_single_mass()
