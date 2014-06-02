""" Socket server for volvo handling temperature and pressure readout """

import SocketServer

class MyUDPHandler(SocketServer.BaseRequestHandler):
    """ UDP Handler class for socket communication """

    def handle(self):
        global setpoint
        global ramp
        global new_ramp

        recieved_data = self.request[0].strip()
        print recieved_data
        data = "test"
        socket = self.request[1]

        if recieved_data[0:12] == "set_setpoint":
            val = float(recieved_data[12:].strip())
            setpoint = val
            print val
            data = "ok"

        if recieved_data[0:13] == "read_setpoint":
            print setpoint
            data = str(setpoint)

        if recieved_data[0:8] == "set_ramp":
            ramp = recieved_data[8:].strip()
            new_ramp = True
            print ramp
            data = 'ok'

        if recieved_data[0:9] == "read_ramp":
            if new_ramp is True:
                data = ramp
                new_ramp = False
            else:
                data = ''
            print 'read_ramp'

        socket.sendto(data, self.client_address)

if __name__ == "__main__":
    HOST, PORT = "130.225.87.213", 9999  # rasppi04
    setpoint = -1
    ramp = None
    new_ramp = False

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
