import sys
import SocketServer
#sys.path.append('../')

#This specific raspberry pi handles temperature control
class MyUDPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        global pressure
        global temperature
        global sample_current

        recieved_data = self.request[0].strip()
        print recieved_data
        data = "test"
        socket = self.request[1]

        if recieved_data[0:12] == "set_pressure":
            val = float(recieved_data[12:].strip())
            pressure = val
            print val
            data = "ok"

        if recieved_data[0:15] == "set_temperature":
            val = float(recieved_data[15:].strip())
            temperature = val
            print val
            data = "ok"

        if recieved_data[0:17] == "set_samplecurrent":
            val = float(recieved_data[17:].strip())
            sample_current = val
            print val
            data = "ok"

        if recieved_data[0:13] == "read_pressure":
            print pressure
            data = str(pressure)

        if recieved_data[0:16] == "read_temperature":
            print temperature
            data = str(temperature)

        if recieved_data[0:18] == "read_samplecurrent":
            print sample_current
            data = str(sample_current)


        socket.sendto(data, self.client_address)

if __name__ == "__main__":
    HOST, PORT = "130.225.87.191", 9999 #robertj

    pressure       = -1
    temperature    = -1
    sample_current = -1

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
