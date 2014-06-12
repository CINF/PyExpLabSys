import sys
import SocketServer
sys.path.append('../../')
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

# Array containing the controllers actually connected
bronk_present = {}
print name
counter = 0
for i in range(0,8):

    if name[i] == 'M13201551A':
        pressure = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i), 5)
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
        if received_data == "read_all":
            print "read_all"
            data = ''
            for i in range(0, len(bronk_present)):
                if bronk_present[i] == 'flow1':
                    data = data + '1:' + str(flow1.read_measure()) + ','
                if bronk_present[i] == 'flow2':
                    data = data + '2:' +str(flow2.read_measure()) + ','
                if bronk_present[i] == 'flow3':
                    data = data + '3:' + str(flow3.read_measure()) + ','
                if bronk_present[i] == 'flow4':
                    data = data + '4:' + str(flow4.read_measure()) + ','
                if bronk_present[i] == 'flow5':
                    data = data + '5:' + str(flow5.read_measure()) + ','
                if bronk_present[i] == 'flow6':
                    data = data + '6:' + str(flow6.read_measure()) + ','
                if bronk_present[i] == 'pressure':
                    data = data + '0:' + str(pressure.read_measure()) + ','
            #Remove trailing comma
            data = data[:-1]

        if received_data == "read_setpoint_1":
            print "read_setpoint_1"
            data = str(flow1.read_setpoint())
        if received_data == "read_setpoint_2":
            print "read_setpoint_2"
            data = str(flow2.read_setpoint())
        if received_data == "read_setpoint_3":
            print "read_setpoint_2"
            data = str(flow3.read_setpoint())
        if received_data == "read_setpoint_4":
            print "read_setpoint_2"
            data = str(flow4.read_setpoint())
        if received_data == "read_setpoint_5":
            print "read_setpoint_2"
            data = str(flow5.read_setpoint())
        if received_data == "read_setpoint_6":
            print "read_setpoint_2"
            data = str(flow6.read_setpoint())
        if received_data == "read_setpoint_pressure":
            print "read_setpoint_pressure"
            data = str(pressure.read_setpoint())

        if received_data[0:10] == "write_all:":
            print "write_all"
            val = received_data[10:].split(',')
            data = ''
            for i in range(0,len(bronk_present)):
                if bronk_present[i] == 'flow1':
                    flow1.set_setpoint(float(val[0]))
                    data = data + 'flow1,'
                if bronk_present[i] == 'flow2':
                    flow2.set_setpoint(val[1])
                    data = data + 'flow2,'
                if bronk_present[i] == 'flow3':
                    flow3.set_setpoint(float(val[2]))
                    data = data + 'flow3,'
                if bronk_present[i] == 'flow4':
                    flow4.set_setpoint(float(val[3]))
                    data = data + 'flow4,'
                if bronk_present[i] == 'flow5':
                    flow5.set_setpoint(float(val[4]))
                    data = data + 'flow5,'
                if bronk_present[i] == 'flow6':
                    flow6.set_setpoint(float(val[5]))
                    data = data + 'flow6,'
                if bronk_present[i] == 'pressure':
                    pressure.set_setpoint(float(val[6]))
                    data = data + 'pressure,'
            data = data[:-1]

        if received_data[0:11] == "set_flow_1:":
            val = float(received_data[11:].strip())
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
    HOST, PORT = "130.225.86.123", 9998 #Rasppi24

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
