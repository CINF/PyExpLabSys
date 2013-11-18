import sys
import SocketServer
#sys.path.append('../')

#This specific raspberry pi handles temperature control
class MyUDPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        global setpoint
        global hp_temp

        recieved_data = self.request[0].strip()
        data = "test"
        socket = self.request[1]

        if recieved_data[0:11] == "set_hp_temp":
            val = float(recieved_data[11:].strip())
            print val
            hp_temp = val
            data = "ok"
        if recieved_data[0:12] == "read_hp_temp":
            print "read_hp_temp"
            print hp_temp
            data = str(hp_temp)

        if recieved_data[0:12] == "set_setpoint":
            val = float(recieved_data[13:].strip())
            setpoint = val
            data = "ok"
            print val
        if recieved_data[0:13] == "read_setpoint":
            print "read_setpoint"
            data = str(setpoint)
        
        socket.sendto(data, self.client_address)

if __name__ == "__main__":
    HOST, PORT = "130.225.86.188", 9990 #rasppi19

    hp_temp = -998
    setpoint = -8888

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
