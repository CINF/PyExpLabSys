import sys
import SocketServer
#sys.path.append('../')

#This specific raspberry pi handles temperature control
class MyUDPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        global rosemount_calibrated
        global rosemount_raw
        global temperature_1
        global temperature_2
        global temperature_5

        recieved_data = self.request[0].strip()
        data = "test"
        socket = self.request[1]

        if recieved_data[0:24] == "set_rosemount_calibrated":
            val = float(recieved_data[24:].strip())
            rosemount_calibrated = val
            print val
            data = "ok"

        if recieved_data[0:17] == "set_rosemount_raw":
            val = float(recieved_data[17:].strip())
            rosemount_raw = val
            print val
            data = "ok"

        if recieved_data[0:17] == "set_temperature_1":
            val = float(recieved_data[17:].strip())
            temperature_1 = val
            print val
            data = "ok"

        if recieved_data[0:17] == "set_temperature_5":
            val = float(recieved_data[17:].strip())
            temperature_5 = val
            print val
            data = "ok"

        if recieved_data[0:17] == "set_temperature_2":
            val = float(recieved_data[17:].strip())
            temperature_2 = val
            print val
            data = "ok"

        if recieved_data[0:25] == "read_rosemount_calibrated":
            print recieved_data[0:25]
            data = str(rosemount_calibrated)

        if recieved_data[0:18] == "read_rosemount_raw":
            print recieved_data[0:18]
            data = str(rosemount_raw)

        if recieved_data[0:18] == "read_temperature_1":
            print recieved_data[0:18]
            data = str(temperature_1)

        if recieved_data[0:18] == "read_temperature_2":
            print recieved_data[0:18]
            data = str(temperature_2)

        if recieved_data[0:18] == "read_temperature_5":
            print recieved_data[0:18]
            data = str(temperature_5)

        socket.sendto(data, self.client_address)

if __name__ == "__main__":
    HOST, PORT = "130.225.86.183", 9999 #rasppi14

    rosemount_calibrated = -1
    rosemount_raw = -1
    temperature_1 = -1
    temperature_2 = -1
    temperature_5 = -1



    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
