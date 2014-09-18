import sys
import SocketServer
sys.path.append('../../')
import brooks

flow1 = brooks.Brooks('/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWDN166-if00-port0')


#This specific raspberry pi communication with mass flow and pressure controllers
class MyUDPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        received_data = self.request[0].strip()
        data = "test"
        socket = self.request[1]

        if received_data == "read_flow_1":
            print "read_flow_1"
            data = str(flow1.read_flow())

        if received_data[0:11] == "set_flow_1:":
            val = float(received_data[11:].strip())
            flow1.set_flow(val)
            data = "ok"


        socket.sendto(data, self.client_address)

if __name__ == "__main__":
    HOST, PORT = "10.54.7.53", 9997 #Rasppi53

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
