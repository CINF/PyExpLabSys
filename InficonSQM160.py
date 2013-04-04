import serial
import time
import SocketServer

class InficonSQM160():

    def __init__(self):
        self.f = serial.Serial(port='/dev/ttyUSB0',baudrate=9600,timeout=2,bytesize=serial.EIGHTBITS,xonxoff=True)
        
    def comm(self,command):
        length = chr(len(command) + 34)
        crc = self.crc_calc(length + command)        
        command = '!' + length + command + crc[0] + crc[1]
        self.f.write(command)
        time.sleep(0.1)
        reply = self.f.read(self.f.inWaiting())

        crc = self.crc_calc(reply[1:-2])
        #print "Length: " + str(ord(reply[1]) - 34)
        #print "Reply: " + reply
        crc_ok = (reply[-2] == crc[0] and reply[-1] == crc[1])
        #print "Calculated crc: " + str(ord(crc[0])) + ' ' + str(ord(crc[1]))
        #print "Calculated crc: " + bin(ord(crc[0])) + ' ' + bin(ord(crc[1]))
        #print "Correct crc: " + str(ord(reply[-2])) + ' ' + str(ord(reply[-1]))
        #print "Correct crc: " + bin(ord(reply[-2])) + ' ' + bin(ord(reply[-1]))
        if crc_ok:    #Remember to also handle the error case...
            return reply[3:-2]
        else:
            pass
            #print("Error: " + reply)

    def crc_calc(self,input_string):
        command_string = []
    
        for i in range(0,len(input_string)):
            command_string.append(ord(input_string[i]))
            
        crc = int('3fff',16)
        mask = int('2001',16)

        for command in command_string:
            crc = command ^ crc
            for i in range(0,8):
                old_crc = crc
                crc  = crc >> 1
                if old_crc % 2 == 1:
                    crc = crc ^ mask

        crc1_mask = int('1111111',2)
        crc1 = chr((crc & crc1_mask) + 34)
        crc2 = chr((crc >> 7) + 34)
        return(crc1,crc2)
        
    def show_version(self):
        command = '@'
        print self.comm(command)

    def show_film_parameters(self,film):
        command = 'A1?'
        print self.comm(command)
        
    def rate(self,channel):
        command = 'L' + str(channel)
        value_string = self.comm(command)
        rate = float(value_string)
        return(rate)

    def thickness(self,channel):
        command = 'N' + str(channel)
        value_string = self.comm(command)
        thickness = float(value_string)        
        return(thickness)
        
    def frequency(self,channel):
        command = 'P' + str(channel)
        value_string = self.comm(command)
        frequency = float(value_string)        
        return(frequency)

    def CrystalLife(self,channel):
        command = 'R' + str(channel)
        value_string = self.comm(command)
        life = float(value_string)        
        return(life)

        

inficon = InficonSQM160()
class MyUDPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        recieved_data = self.request[0].strip()
        data = "test"
        socket = self.request[1]
        print recieved_data
        if recieved_data == "rate":
            data = str(inficon.rate(1))
        if recieved_data == "thickness":
            data = str(inficon.thickness(1))
        if recieved_data == "frequency":
            data = str(inficon.frequency(1))
        if recieved_data == "crystallife":
            data = str(inficon.CrystalLife(1))
        socket.sendto(data, self.client_address)

		
if __name__ == "__main__":
    HOST, PORT = "agilent", 9999

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
    #inficon = InficonSQM160()
    #inficon.show_version()
    #inficon.rate(1)
    #inficon.thickness(1)
    #inficon.frequency(1)
    #inficon.CrystalLife(1)
    #inficon.show_film_parameters(1)
    

