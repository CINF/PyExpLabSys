import sys
import SocketServer

class MyUDPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        global setpoint

        received_data = self.request[0].strip()
        data = "test"
        socket = self.request[1]

        if received_data == "read_setpoint_pressure":
            print "read_setpoint_pressure"
            data = str(setpoint)

        if received_data[0:13] == "set_pressure:":
            val = float(received_data[13:].strip())
            setpoint = val
            print "set_pressure"
            data = "ok"

        socket.sendto(data, self.client_address)


if __name__ == "__main__":
    HOST, PORT = "130.225.86.182", 9999 #Rasppi13
    setpoint = 2000
    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
