import sys
import SocketServer
import time
sys.path.append('../')
import polyscience_4100

#This specific raspberry pi handles temperature control
class MyUDPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        recieved_data = self.request[0].strip()
        data = "test"
        socket = self.request[1]

        if recieved_data[0:12] == "set_setpoint":
            try:
                val = int(float(recieved_data[12:].strip()))
                success = chiller.set_setpoint(val)
            except:
                data = 'failed'
            time.sleep(0.5)
            if success:
                data = "ok"
            else:
                data = "failed"

        if recieved_data[0:13] == "read_setpoint":
            val = chiller.read_setpoint()
            #print "read_setpoint"
            data = str(val)

        if recieved_data[0:11] == "read_status":
            val = chiller.read_status()
            #print "read_status"
            data = val

        if recieved_data[:] == "read_ambient_temperature":
            val = chiller.read_ambient_temperature()
            #print "read_ambient_temperature"
            data = str(val)

        if recieved_data[:] == "read_temperature":
            val = chiller.read_temperature()
            #print "read_temperature"
            data = str(val)

        if recieved_data[:] == "read_pressure":
            val = chiller.read_pressure()
            #print "read_pressure"
            data = str(val)
        
        if recieved_data[:] == "read_flow_rate":
            val = chiller.read_flow_rate()
            #print "read_flow_rate"
            data = str(val)


        if recieved_data[0:7] == "turn_on":
            val = chiller.turn_unit_on(True)
            time.sleep(1)
            data = val
            print val

        if recieved_data[:] == "turn_off":
            val = chiller.turn_unit_on(False)
            time.sleep(1)
            data = val
            print val
        
        socket.sendto(data, self.client_address)

if __name__ == "__main__":
    HOST, PORT = "130.225.86.189", 9759 #rasppi20
    chiller = polyscience_4100.Polyscience_4100()

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
