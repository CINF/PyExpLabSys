import sys
import SocketServer

#This specific code return values when needed
                         
class MyUDPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        global temperature_outside
        global temperature_1
        global temperature_2

        recieved_data = self.request[0].strip()
        data = "test"
        socket = self.request[1]

        if recieved_data[0:23] == "set_temperature_outside":
            val = float(recieved_data[24:].strip())
            temperature_outside = val
            print val

        if recieved_data[0:17] == "set_temperature_1":
            val = float(recieved_data[17:].strip())
            temperature_1 = val
            print val
            data = "ok"

        if recieved_data[0:17] == "set_temperature_2":
            val = float(recieved_data[17:].strip())
            temperature_2 = val
            print val
            data = "ok"

        if recieved_data[0:24] == "read_temperature_outside":
            print "temperature_outside"
            data = str(temperature_outside)

        if recieved_data[0:18] == "read_temperature_1":
            print "temperature_1"
            data = str(temperature_1)

        if recieved_data[0:18] == "read_temperature_2":
            print "temperature_2"
            data = str(temperature_2)

        socket.sendto(data, self.client_address)

if __name__ == "__main__":
   HOST, PORT = "127.0.0.1", 9999 #localhost
   temperature_outside = -1
   temperature_1 = -1
   temperature_2 = -1

   server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
   server.serve_forever()
