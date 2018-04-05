import sys
import SocketServer
#sys.path.append('../')

#This specific raspberry pi handles temperature control
class MyUDPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        global ion_gauge_pressure

        recieved_data = self.request[0].strip()
        data = "test"
        socket = self.request[1]

        if recieved_data[0:12] == "set_iongauge":
            val = float(recieved_data[12:].strip())
            ion_gauge_pressure = val
            print val
            data = "ok"

        if recieved_data[0:13] == "read_iongauge":
            print ion_gauge_pressure
            data = str(ion_gauge_pressure)

        socket.sendto(data, self.client_address)

if __name__ == "__main__":
    HOST, PORT = "130.225.87.218", 9999 #rasppi09

    ion_gauge_pressure = -1

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
