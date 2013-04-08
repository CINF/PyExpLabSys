import sys
import SocketServer
sys.path.append('../')
import bronkhorst

# This list is magical! ttyUSB numbers are changed upon reboot
flow1 = bronkhorst.Bronkhorst('/dev/ttyUSB0')
flow2 = bronkhorst.Bronkhorst('/dev/ttyUSB1')
flow3 = bronkhorst.Bronkhorst('/dev/ttyUSB2')
flow4 = bronkhorst.Bronkhorst('/dev/ttyUSB3')
flow5 = bronkhorst.Bronkhorst('/dev/ttyUSB4')
flow6 = bronkhorst.Bronkhorst('/dev/ttyUSB5')
pressure = bronkhorst.Bronkhorst('/dev/ttyUSB6')


#This specific raspberry pi communication with mass flow and pressure controllers
class MyUDPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        received_data = self.request[0].strip()
        data = "test"
        socket = self.request[1]

        if received_data == "read_flow_1":
            print "read_flow_1"
            data = str(flow1.read_measure(10))
        if received_data == "read_flow_2":
            print "read_flow_2"
            data = str(flow2.read_measure(10))
        if received_data == "read_flow_3":
            print "read_flow_3"
            data = str(flow3.read_measure(10))
        if received_data == "read_flow_4":
            print "read_flow_4"
            data = str(flow4.read_measure(10))
        if received_data == "read_flow_5":
            print "read_flow_5"
            data = str(flow5.read_measure(2.5))
        if received_data == "read_flow_6":
            print "read_flow_6"
            data = str(flow6.read_measure(10))
        if received_data == "read_pressure":
            print "read_flow_pressure"
            data = str(pressure.read_measure(10))
        if received_data[0:11] == "set_flow_1:":
            val = float(received_data[11:].strip())
            flow1.set_setpoint(val,10)
            data = "ok"
        if received_data[0:11] == "set_flow_2:":
            val = float(received_data[11:].strip())
            flow2.set_setpoint(val,10)
            data = "ok"
        if received_data[0:11] == "set_flow_3:":
            val = float(received_data[11:].strip())
            flow3.set_setpoint(val,10)
            data = "ok"
        if received_data[0:11] == "set_flow_4:":
            val = float(received_data[11:].strip())
            flow4.set_setpoint(val,10)
            data = "ok"
        if received_data[0:11] == "set_flow_5:":
            val = float(received_data[11:].strip())
            flow5.set_setpoint(val,10)
            data = "ok"
        if received_data[0:11] == "set_flow_6:":
            val = float(received_data[11:].strip())
            flow6.set_setpoint(val,10)
            data = "ok"
        if received_data[0:13] == "set_pressure:":
            val = float(received_data[13:].strip())
            pressure.set_setpoint(val,10)
            data = "ok"

        socket.sendto(data, self.client_address)

if __name__ == "__main__":
    HOST, PORT = "130.225.86.185", 9999 #Rasppi16

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
