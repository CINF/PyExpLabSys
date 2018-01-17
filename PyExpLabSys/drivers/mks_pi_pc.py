import serial
import time

class Mks_Pi_Pc():

    def __init__(self, port='/dev/ttyUSB2'):
        self.f = serial.Serial(port, 38400, timeout=1)
        self.macid = 55
        self.fullrange = 2666 #  mbar. In torr the value is 2000

    def checksum(self, command):
        s = 0
        for i in range(0,len(command)):
            s = s+ord(command[i])
            #print ord(command[i])
        return(s%256)

    def comm(self, classid, instanceid, attributeid, write=False, macid=None, length=3, data=''):
        if macid is None:
            macid = self.macid
        if write is True:
            command = int('81',16)
        else:
            command = int('80',16)

        comm = chr(2) #STX
        comm += chr(command)
        comm += chr(length) # This could properly be found algorithmically
        comm += chr(classid)
        comm += chr(instanceid)
        comm += chr(attributeid)
        comm += data
        comm += chr(0) #Required by protocol
        checksum = self.checksum(comm)
        self.f.write(chr(macid) + comm + chr(checksum))
        time.sleep(0.1)
        reply = self.f.read(self.f.inWaiting())
        reply_checksum = reply[-1]
        if not write:
            if ord(reply_checksum) == self.checksum(reply[1:-1]):
                length = ord(reply[4])
                reply = reply[8:8+length-3] #According to protocol
            else:
                print('Error')
        else:
            if not ord(reply[0]) == 6:
                print('Error')
        return(reply)

    def convert_value_from_mks(self, value):
        msb = value[1]
        lsb = value[0]
        hex_value = hex(ord(msb))[2:].zfill(2) + hex(ord(lsb))[2:].zfill(2)
        full_scale = int('C000',16) - int('4000',16)
        calibrated_value = (1.0 * self.fullrange * (int(hex_value,16) - int('4000',16))) / full_scale
        return(calibrated_value)

    def set_setpoint(self, setpoint):
        full_scale = int('C000',16) - int('4000',16)
        mks_setpoint = (full_scale * setpoint / self.fullrange) + int('4000',16)
        hex_setpoint = hex(mks_setpoint)[2:]
        assert(len(hex_setpoint)==4)
        msb = chr(int(hex_setpoint[0:2], 16))
        lsb = chr(int(hex_setpoint[2:4], 16))
        self.comm(int('69',16),1,int('a4',16), length=5, write=True, data=lsb+msb)

    def read_mac_id(self):
        macid = self.comm(3, 1, 1)
        return(ord(macid))

    """
    def query_full_range(self):
        fullrange = self.comm(int('66',16), 0, int('a0',16))
        #print ord(fullrange[0])
        print ord(fullrange[2])
        #print hex(ord(fullrange[0]))
        #print hex(ord(fullrange[1]))

        print self.convert_value_from_mks(fullrange[1] + fullrange[0])
        #print mks.convert_value_from_mks(fullrange[0:2])
        #for i in range(0, len(fullrange)):
        #    print ord(fullrange[i])
        return('')
    """

    def read_setpoint(self):
        setpoint = self.comm(int('6a',16), 1, int('a6',16))
        return(self.convert_value_from_mks(setpoint))

    def read_pressure(self):
        pressure = self.comm(int('6a',16), 1, int('a9',16))
        return(self.convert_value_from_mks(pressure))


if __name__ == '__main__':
    mks = Mks_Pi_Pc()
    #print mks.read_mac_id()
    print("Setpoint: " + str(mks.read_setpoint()))
    print("Pressure: " + str(mks.read_pressure()))
    mks.set_setpoint(500)
    print("Setpoint: " + str(mks.read_setpoint()))

    print(mks.query_full_range())
