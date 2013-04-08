import sys
import SocketServer
sys.path.append('../')
import bronkhorst

bronkhorst = bronkhorst.Bronkhorst()

#This specific raspberry pi communication with mass flow and pressure controllers

class MyUDPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        recieved_data = self.request[0].strip()
        data = "test"
        socket = self.request[1]
        print recieved_data

        if recieved_data == "read_value_flow1":
            data = str(bronkhorst.ReadValue(flow1))
        if recieved_data == "read_value_flow2":
            data = str(bronkhorst.ReadValue(flow2))
        if recieved_data == "read_value_flow3":
            data = str(bronkhorst.ReadValue(flow3))
        if recieved_data == "read_value_flow4":
            data = str(bronkhorst.ReadValue(flow4))
        if recieved_data == "read_value_flow5":
            data = str(bronkhorst.ReadValue(flow5))
        if recieved_data == "read_value_flow6":
            data = str(bronkhorst.ReadValue(flow6))
        if recieved_data == "read_value_pressure":
            data = str(bronkhorst.ReadValue(pressure))
        if recieved_data == "set_value_flow1":
            data = str(bronkhorst.SetValue(flow1))
        if recieved_data == "set_value_flow1":
            data = str(bronkhorst.SetValue(flow2))
        if recieved_data == "set_value_flow1":
            data = str(bronkhorst.SetValue(flow3))
        if recieved_data == "set_value_flow1":
            data = str(bronkhorst.SetValue(flow4))
        if recieved_data == "set_value_flow1":
            data = str(bronkhorst.SetValue(flow5))
        if recieved_data == "set_value_flow1":
            data = str(bronkhorst.SetValue(flow6))
        if recieved_data == "set_value_pressure":
            data = str(bronkhorst.SetValue(pressure))
        socket.sendto(data, self.client_address)

if __name__ == "__main__":
    HOST, PORT = "130.225.86.xxx", 9999 #Rasppi16

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
