import sys
import SocketServer
sys.path.append('../')
import bronkhorst

# Code for assigning the controllers to proper /dev/tty*
name = {}

bronk = bronkhorst.Bronkhorst('/dev/ttyUSB0')
name[0] = bronk.read_serial()
name[0] = name[0].strip()

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

for i in range(0,8):
    print name[i]

#bronkhorst = {}

for i in range(0,6):
    if name[i] == 'x':
        pressure = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i), 2.5)
        print("pressure: /dev/ttyUSB" + str(i))

    if name[i] == 'M11200362C':
        flow1 = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i), 10)
        print("flow1: /dev/ttyUSB" + str(i))

    if name[i] == 'x':
        flow2 = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i), 10)
        print("flow2: /dev/ttyUSB" + str(i))

    if name[i] == 'x':
        flow3 = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i), 10)
        print("flow3: /dev/ttyUSB" + str(i))

    if name[i] == 'x':
        flow4 = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i), 10)
        print("flow4: /dev/ttyUSB" + str(i))

    if name[i] == 'x':
        flow5 = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i), 10)
        print("flow5: /dev/ttyUSB" + str(i))

    if name[i] == 'x':
        flow6 = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i), 10)
        print("flow6: /dev/ttyUSB" + str(i))


#This specific raspberry pi communication with mass flow and pressure controllers
class MyUDPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        received_data = self.request[0].strip()
        data = "test"
        socket = self.request[1]

        if received_data == "read_flow_1":
            print "read_flow_1"
            data = str(flow1.read_measure())
        if received_data == "read_flow_2":
            print "read_flow_2"
            data = str(flow2.read_measure())
        if received_data == "read_flow_3":
            print "read_flow_3"
            data = str(flow3.read_measure())
        if received_data == "read_flow_4":
            print "read_flow_4"
            data = str(flow4.read_measure())
        if received_data == "read_flow_5":
            print "read_flow_5"
            data = str(flow5.read_measure())
        if received_data == "read_flow_6":
            print "read_flow_6"
            data = str(flow6.read_measure())
        if received_data == "read_pressure":
            print "read_pressure"
            data = str(pressure.read_measure())
        if received_data[0:11] == "set_flow_1:":
            val = float(received_data[11:].strip())
            print val
            flow1.set_setpoint(val)
            data = "ok"
        if received_data[0:11] == "set_flow_2:":
            val = float(received_data[11:].strip())
            flow2.set_setpoint(val)
            data = "ok"
        if received_data[0:11] == "set_flow_3:":
            val = float(received_data[11:].strip())
            flow3.set_setpoint(val)
            data = "ok"
        if received_data[0:11] == "set_flow_4:":
            val = float(received_data[11:].strip())
            flow4.set_setpoint(val)
            data = "ok"
        if received_data[0:11] == "set_flow_5:":
            val = float(received_data[11:].strip())
            flow5.set_setpoint(val)
            data = "ok"
        if received_data[0:11] == "set_flow_6:":
            val = float(received_data[11:].strip())
            flow6.set_setpoint(val)
            data = "ok"
        if received_data[0:13] == "set_pressure:":
            val = float(received_data[13:].strip())
            pressure.set_setpoint(val)
            data = "ok"

        socket.sendto(data, self.client_address)

if __name__ == "__main__":
    HOST, PORT = "130.225.86.185", 9999 #Rasppi16

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
