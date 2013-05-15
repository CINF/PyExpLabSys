import sys
import SocketServer
sys.path.append('../')
import bronkhorst

# Code for assigning the controllers to proper /dev/tty*
name = {}

bronk = bronkhorst.Bronkhorst('/dev/ttyUSB0')
name[0] = bronk.read_serial()
name[0] = name[0].strip()

'''
bronk = bronkhorst.Bronkhorst('/dev/ttyUSB1')
name[1] = bronk.read_serial()
name[1] = name[1].strip()

bronk = bronkhorst.Bronkhorst('/dev/ttyUSB2')
name[2] = bronk.read_serial()
name[2] = name[2].strip()

bronk = bronkhorst.Bronkhorst('/dev/ttyUSB3')
name[3] = bronk.read_serial()
name[3] = name[3].strip()

bronk = bronkhorst.Bronkhorst('/dev/ttyUSB4')
name[4] = bronk.read_serial()
name[4] = name[4].strip()

bronk = bronkhorst.Bronkhorst('/dev/ttyUSB5')
name[5] = bronk.read_serial()
name[5] = name[5].strip()

bronk = bronkhorst.Bronkhorst('/dev/ttyUSB6')
name[6] = bronk.read_serial()
name[6] = name[6].strip()

bronk = bronkhorst.Bronkhorst('/dev/ttyUSB7')
name[7] = bronk.read_serial()
name[7] = name[7].strip()
'''

# Array containing the controllers actually connected
bronk_present = {}

counter = 0
for i in range(0,1):

    if name[i] == 'M11210022A':
        pressure = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i), 2.5)
        print("pressure:/dev/ttyUSB" + str(i) + ', serial:' + name[i])
        bronk_present[counter] = 'pressure'
        pressure.set_control_mode() #Change to accept setpoint from rs232 interface
        counter = counter + 1

    if name[i] == 'x':
        flow1 = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i), 10)
        print("flow1:/dev/ttyUSB" + str(i) + ', serial:' + name[i])
        bronk_present[counter] = 'flow1'
        counter = counter + 1

    if name[i] == 'x':
        flow2 = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i), 10)
        print("flow2:/dev/ttyUSB" + str(i) + ', serial:' + name[i])
        bronk_present[counter] = 'flow2'
        counter = counter + 1

    if name[i] == 'x':
        flow3 = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i), 5)
        print("flow3:/dev/ttyUSB" + str(i) + ', serial:' + name[i])
        bronk_present[counter] = 'flow3'
        counter = counter + 1

    if name[i] == 'x':
        flow4 = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i), 5)
        print("flow4:/dev/ttyUSB" + str(i) + ', serial:' + name[i])
        bronk_present[counter] = 'flow4'
        counter = counter + 1

    if name[i] == 'x':
        flow5 = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i), 10)
        print("flow5:/dev/ttyUSB" + str(i) + ', serial:' + name[i])
        bronk_present[counter] = 'flow5'
        counter = counter + 1

    if name[i] == 'x':
        flow6 = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i), 1)
        print("flow6:/dev/ttyUSB" + str(i) + ', serial:' + name[i])
        bronk_present[counter] = 'flow6'
        counter = counter + 1

#This specific raspberry pi communication with mass flow and pressure controllers
class MyUDPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        received_data = self.request[0].strip()
        data = "test"
        socket = self.request[1]

        if received_data == "read_pressure":
            print "read_pressure"
            data = str(pressure.read_measure())

        if received_data == "read_setpoint_pressure":
            print "read_setpoint_pressure"
            data = str(pressure.read_setpoint())

        if received_data[0:13] == "set_pressure:":
            val = float(received_data[13:].strip())
            pressure.set_setpoint(val)
            print "set_pressure"
            data = "ok"

        socket.sendto(data, self.client_address)


if __name__ == "__main__":
    HOST, PORT = "130.225.86.182", 9999 #Rasppi13

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
