import sys
import SocketServer

class MyUDPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        global buffer_pressure
        global chamber_pressure
        global flows
        global temperature

        recieved_data = self.request[0].strip()
        data = "test"
        socket = self.request[1]

        comm = 'set_buffer'
        if recieved_data[0:len(comm)] == comm:
            print "set_buffer"
            buffer_pressure = recieved_data[len(comm):]
            data = 'ok'

        comm = 'set_chamber_pressure'
        if recieved_data[0:len(comm)] == comm:
            print "set_chamber_pressure"
            chamber_pressure = recieved_data[len(comm):]
            data = 'ok'

        comm = 'set_flows'
        if recieved_data[0:len(comm)] == comm:
            print "set_flows"
            flows = recieved_data[len(comm):]
            data = 'ok'

        comm = 'set_temperature'
        if recieved_data[0:len(comm)] == comm:
            print "set_temperature"
            temperature = recieved_data[len(comm):]
            data = 'ok'

        comm = 'read_temperature'
        if recieved_data[0:len(comm)] == comm:
            print "read_temperature"
            data = temperature

        comm = 'read_flows'
        if recieved_data[0:len(comm)] == comm:
            print "read_flows"
            data = flows

        comm = 'read_chamber_pressure'
        if recieved_data[0:len(comm)] == comm:
            print "read_chamber_pressute"
            data = chamber_pressure

        comm = 'read_buffer'
        if recieved_data[0:len(comm)] == comm:
            print "read_buffer"
            data = buffer_pressure


        socket.sendto(data, self.client_address)


if __name__ == "__main__":
    HOST, PORT = "10.54.7.27", 9999 #Rasppi27
    buffer_pressure = ''
    chamber_pressure = ''
    flows = ''
    temperature = ''
    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
