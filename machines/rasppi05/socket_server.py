import sys
import SocketServer
#sys.path.append('../')

#This specific raspberry pi handles temperature control
class MyUDPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        global setpoint
        global rtd_val

        recieved_data = self.request[0].strip()
        data = "test"
        socket = self.request[1]

        if recieved_data[0:10] == "set_rtdval":
            val = float(recieved_data[11:].strip())
            rtd_val = val
            data = "ok"
        if recieved_data[0:11] == "read_rtdval":
            print "read_rtdval"
            data = str(rtd_val)

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
    HOST, PORT = "10.54.7.5", 9999 #rasppi05

    setpoint = -998
    rtd_val = -888

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
