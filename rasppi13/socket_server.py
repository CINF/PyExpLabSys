import sys
import SocketServer
sys.path.append('../')
import bronkhorst
import mks_925_pirani as mks

# Code for assigning the controllers to proper /dev/tty*
name = {}

bronk = bronkhorst.Bronkhorst('/dev/ttyUSB0')
serial_name = bronk.read_serial()
serial_name = serial_name.strip()
if serial_name != '':
    name[0] = serial_name
    print serial_name

bronk = bronkhorst.Bronkhorst('/dev/ttyUSB1')
serial_name = bronk.read_serial()
serial_name = serial_name.strip()
if serial_name != '':
    name[1] = serial_name
    print serial_name


pirani = mks.mks_comm('/dev/ttyUSB0')
serial_name = pirani.read_serial()
serial_name = serial_name.strip()
if serial_name != '':
    name[0] = serial_name

pirani = mks.mks_comm('/dev/ttyUSB1')
serial_name = pirani.read_serial()
serial_name = serial_name.strip()
if serial_name != '':
    name[1] = serial_name

print name[0]
print name[1]

## Array containing the controllers actually connected
#bronk_present = {}

#counter = 0
for i in range(0,2):

    if name[i] == 'M11200362H':
        pressure = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i), 2.5)
        print("pressure: /dev/ttyUSB" + str(i) + ', serial:' + name[i])
        pressure.set_control_mode() #Change to accept setpoint from rs232 interface

    if name[i] == '1305957886':
        pirani = mks.mks_comm('/dev/ttyUSB' + str(i))
        print("pirani: /dev/ttyUSB" + str(i) + ', serial:' + name[i])

#This specific raspberry pi communication with mass flow and pressure controllers
class MyUDPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        received_data = self.request[0].strip()
        data = "test"
        socket = self.request[1]

        if received_data == "read_pirani":
            #print "read_pirani"
            data = str(pirani.read_pressure())

        if received_data == "read_pressure":
            #print "read_pressure"
            data = str(pressure.read_measure()*1000)

        if received_data == "read_setpoint_pressure":
            #print "read_setpoint_pressure"
            data = str(pressure.read_setpoint()*1000)

        if received_data[0:13] == "set_pressure:":
            val = float(received_data[13:].strip())
            pressure.set_setpoint(val / 1000.0)
            #print "set_pressure"
            data = "ok"

        socket.sendto(data, self.client_address)


if __name__ == "__main__":
    HOST, PORT = "130.225.86.182", 9999 #Rasppi13

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
