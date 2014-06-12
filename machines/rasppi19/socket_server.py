import sys
import SocketServer
#sys.path.append('../')

#This socket server also servers as a communication path
#between master pc logging pressure & temperature and
#massspec program

#This specific raspberry pi handles temperature control
class MyUDPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        global setpoint
        global hp_temp
        global global_pressure
        global global_temperature

        recieved_data = self.request[0].strip()
        data = "test"
        socket = self.request[1]

        comm = 'set_global_temp'
        if recieved_data[0:len(comm)] == comm:
            val = float(recieved_data[len(comm)+1:].strip())
            print val
            global_temperature = val
            data = "ok"

        comm = 'set_global_pressure'
        if recieved_data[0:len(comm)] == comm:
            val = float(recieved_data[len(comm)+1:].strip())
            print val
            global_pressure = val
            data = "ok"

        comm = 'read_global_temp'
        if recieved_data[0:len(comm)] == comm:
            print 'read_global_temp'
            data = str(global_temperature)

        comm = 'read_global_pressure'
        if recieved_data[0:len(comm)] == comm:
            print 'read_global_pressure'
            data = str(global_temperature)

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
    global_pressure = -1
    global_temperature = -1

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
