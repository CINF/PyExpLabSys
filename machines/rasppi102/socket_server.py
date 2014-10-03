import sys
import SocketServer
import PyExpLabSys.drivers.mks_925_pirani as mks_925_pirani

#Assigning of proper /dev/tty*
1107638964
name = {}

mks = mks_925_pirani.mks_comm('/dev/ttyUSB0')
name[0] = mks.read_serial()
name[0] = name[0].strip()

mks = mks_925_pirani.mks_comm('/dev/ttyUSB1')
name[1] = mks.read_serial()
name[1] = name[1].strip()

for i in range(0,2):

    if name[i] == '1107638964':
        mks_buffer = mks_925_pirani.mks_comm('/dev/ttyUSB' + str(i))
        print('Pirani, buffer:/dev/ttyUSB' + str(i) + ', serial:' + name[i])

    if name[i] == '1107638963':
        mks_containment = mks_925_pirani.mks_comm('/dev/ttyUSB' + str(i))
        print('Pirani, containment:/dev/ttyUSB' + str(i) + ', serial:' + name[i])


#This specific raspberry pi handles pressure readout from mks devices
class MyUDPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        recieved_data = self.request[0].strip()
        print recieved_data
        data = "test"
        socket = self.request[1]
        print recieved_data
        if recieved_data == "read_containment":
            data = str(mks_containment.read_pressure())
        if recieved_data == "read_buffer":
            data = str(mks_buffer.read_pressure())
            print data
        socket.sendto(data, self.client_address)

if __name__ == "__main__":
    #HOST, PORT = "130.225.87.216", 9997 #Rasppi07
    HOST, PORT = "10.54.7.102", 9997 #Rasppi102

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
