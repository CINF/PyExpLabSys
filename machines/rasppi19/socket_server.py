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
        print recieved_data
        data = "test"
        socket = self.request[1]

        comm = 'set_global_temp'
        if recieved_data[0:len(comm)] == comm:
            val = float(recieved_data[len(comm)+1:].strip())
            #print val
            global_temperature = val
            data = "ok"

        comm = 'set_global_pressure'
        if recieved_data[0:len(comm)] == comm:
            val = float(recieved_data[len(comm)+1:].strip())
            #print val
            global_pressure = val
            data = "ok"

        comm = 'read_global_temp'
        if recieved_data[0:len(comm)] == comm:
            print 'read_global_temp'
            data = str(global_temperature)

        comm = 'read_global_pressure'
        if recieved_data[0:len(comm)] == comm:
            #print 'read_global_pressure'
            data = str(global_pressure)
            
        comm = "set_hp_temp"
        if recieved_data[0:len(comm)] == comm:
            val = float(recieved_data[len(comm)+1:].strip())
            #print val
            hp_temp = val
            data = "ok"
        
        comm = "read_hp_temp"
        if recieved_data[0:len(comm)] == comm:
            #print "read_hp_temp"
            #print hp_temp
            data = str(hp_temp)
        
        comm = "set_setpoint"
        if recieved_data[0:len(comm)] == comm:
            #print recieved_data
            val = float(recieved_data[len(comm)+1:].strip())
            #print recieved_data[13:].strip()
            setpoint = val
            data = "ok"
            print val
        
        comm = "read_setpoint"
        if recieved_data[0:len(comm)] == comm:
            print "read_setpoint"
            data = str(setpoint)
        print recieved_data + data
        socket.sendto(data, self.client_address)

if __name__ == "__main__":
    HOST, PORT = "10.54.7.19", 9990 #rasppi19

    hp_temp = -998
    setpoint = -8888
    global_pressure = -1
    global_temperature = -1

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
