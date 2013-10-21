import serial
import time

class TurboController():
    def __init__(self, port='/dev/ttyUSB0'):
        self.f = serial.Serial(port,9600)
        self.f.stopbits = 2
        self.adress = 1

    def comm(self, command, read=True):
        adress_string = str(self.adress).zfill(3)

        if read:
            action = '00'
            datatype = '=?'
            length = str(len(datatype)).zfill(2)
            command = action + command + length + datatype

        #print command
        crc = self.crc_calc(adress_string + command)
        self.f.write(adress_string + command + crc + '\r')
        a = ''
        response = ''
        while not (a == '\r'):
            a = self.f.read()
            response += a
        #print 'Adress: ' + response[0:3]
        #print 'Action: '  + response[3:5]
        #print 'Parameter: ' + response[5:8]
        #print 'Length: ' + response[8:10]
        length = int(response[8:10])
        #print length
        reply = response[10:10+length]
        crc = response[10+length:10+length+3]
        #print self.crc_calc(response[0:10+length]) == crc
        if crc:
            return reply
        else:
            return 'Error!'

    def crc_calc(self, command):
        crc = 0
        for s in command:
            crc +=  ord(s)
        crc = crc % 256
        crc_string = str(crc).zfill(3)
        return crc_string

    def read_rotation_speed(self):
        command = '309'
        reply = self.comm(command, True)
        print int(reply)

    def read_gas_mode(self):
        command = '027'
        reply = self.comm(command, True)
        mode = int(reply)
        if mode == 0:
            return 'Heavy gasses'
        if mode == 1:
            return 'Light gasses'
        if mode == 2:
            return 'Helium'

    def is_pump_accelerating(self):
        command = '307'
        reply = self.comm(command, True)
        if int(reply) == 1:
            return True
        else:
            return False

    def turn_pump_on(self, off=False):
        print off
        if not off:
            command = '1001006111111'
            print 'On'
        else:
            command = '1001006000000'
        self.comm(command, False)

    def read_temperature(self):
        command = '326'
        reply = self.comm(command, True)
        elec = int(reply)

        command = '330'
        reply = self.comm(command, True)
        bottom = int(reply)

        command = '342'
        reply = self.comm(command, True)
        bearings = int(reply)

        command = '346'
        reply = self.comm(command, True)
        motor = int(reply)

        return_val = {}
        return_val['elec'] = elec
        return_val['bottom'] = bottom
        return_val['bearings'] = bearings
        return_val['motor'] = motor
        return return_val

    def read_drive_power(self):
        command = '310'
        reply = self.comm(command, True)
        current = int(reply)/100.0

        command = '313'
        reply = self.comm(command, True)
        print reply
        voltage = int(reply)/100.0

        command = '316'
        reply = self.comm(command, True)
        power = int(reply)

        return_val = {}
        return_val['voltage'] = voltage
        return_val['current'] = current
        return_val['power'] = power
        return return_val

if __name__ == '__main__':
    T = TurboController()
    T.read_rotation_speed()
    T.turn_pump_on()
    time.sleep(10)
    T.read_rotation_speed()
    print 'Pump is accelerating: '  + str(T.is_pump_accelerating())
    print 'Gas mode: ' + T.read_gas_mode()
    print 'Power: ' + str(T.read_drive_power())
    print 'Temperature: ' + str(T.read_temperature())
    time.sleep(2)
    #T.read_rotation_speed()
    T.turn_pump_on(off = True)
    #time.sleep(2)
    #T.read_rotation_speed()
    #time.sleep(2)
    #T.read_rotation_speed()
    #time.sleep(2)
    #T.read_rotation_speed()
    time.sleep(2)
    T.read_rotation_speed()


"""
s = '001'

#command = s + '0030902=?'
command = s + '0034902=?'
crc_string = crc_calc(command)

f.write(command + crc_string + '\r')
time.sleep(0.2)
print f.inWaiting()
print f.read(f.inWaiting())
"""
