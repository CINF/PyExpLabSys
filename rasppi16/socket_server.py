import sys
import SocketServer
sys.path.append('../')
import bronkhorst

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
        recieved_data = self.request[0].strip()
        data = "test"
        socket = self.request[1]
        print recieved_data

        if recieved_data == "read_value_flow1":
            data = str(flow1.read_measure(10))
        if recieved_data == "read_value_flow2":
            data = str(flow2.read_measure(10))
        if recieved_data == "read_value_flow3":
            data = str(flow3.read_measure(10))
        if recieved_data == "read_value_flow4":
            data = str(flow4.read_measure(10))
        if recieved_data == "read_value_flow5":
            data = str(flow5.read_measure(10))
        if recieved_data == "read_value_flow6":
            data = str(flow6.read_measure(10))
        if recieved_data == "read_value_pressure":
            data = str(pressure.read_measure(10))
        if recieved_data == "set_value_flow1":
            data = str(flow1.set_setpoint(flow1,10))
        if recieved_data == "set_value_flow1":
            data = str(flow1.set_setpoint(flow1,10))
        if recieved_data == "set_value_flow1":
            data = str(flow1.set_setpoint(flow1,10))
        if recieved_data == "set_value_flow1":
            data = str(flow1.set_setpoint(flow1,10))
        if recieved_data == "set_value_flow1":
            data = str(flow1.set_setpoint(flow1,10))
        if recieved_data == "set_value_flow1":
            data = str(flow1.set_setpoint(flow1,10))
        if recieved_data == "set_value_pressure":
            data = str(flow1.set_setpoint(flow1,2.5))
        socket.sendto(data, self.client_address)

if __name__ == "__main__":
    HOST, PORT = "130.225.86.xxx", 9999 #Rasppi16

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
