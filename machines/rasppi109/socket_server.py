#import sys
import SocketServer
import threading
import time

import PyExpLabSys.drivers.agilent_34972A as multiplexer
import sys
import ReadTofVoltages
#sys.path.append('../')


class SlowProcess(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.bias_string = ''
        self.update = False
        self.running = True
        self.recent_update = -1

    def update_bias_string(self):
        self.bias_string = ReadTofVoltages.read_voltages()

    def run(self):
        while self.running:
            if self.update:
                self.update_bias_string()
                time.sleep(0.1)
                self.recent_update = 20
                self.update = False
            else:
                self.recent_update = self.recent_update - 1
                time.sleep(1)
            if self.recent_update < 0:
                self.bias_string = ''
        

class MyUDPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        global bias
        global pec
        global agilent
        global slow_handler

        recieved_data = self.request[0].strip()
        data = "test"
        socket = self.request[1]

        command = 'start_tof_measurement'
        if recieved_data[0:len(command)] == command:
            val = float(recieved_data[len(command)+1:].strip())
            voltage = val
            string = "SOURCE:VOLT " + str(voltage/500.0) + ", (@204)"
            agilent.scpi_comm(string)
            slow_handler.update = True
            data = 'ok'

        command = 'read_voltages'
        if recieved_data[0:len(command)] == command:
            data = slow_handler.bias_string

        command = 'stop_tof_measurement'
        if recieved_data[0:len(command)] == command:
            voltage = 0
            string = "SOURCE:VOLT " + str(voltage/500.0) + ", (@204)"
            agilent.scpi_comm(string)
            data = 'ok'

        command = 'read_bias'
        if recieved_data[0:len(command)] == command:
            data = str(bias)

        command = 'set_bias'
        if recieved_data[0:len(command)] == command:
            val = float(recieved_data[len(command)+1:].strip())
            bias = val
            data = "ok"
            print val
            print 'set_bias'

        command = 'aps' #Ask pause status
        if recieved_data[0:len(command)] == command:
            data = str(slow_handler.update)
            print data

        socket.sendto(data, self.client_address)

if __name__ == "__main__":
    HOST, PORT = '10.54.7.109', 9696 #rasppi109

    bias     = -1
    pec = False
    agilent = multiplexer.Agilent34972ADriver(name='tof-agilent-34972a')

    slow_handler = SlowProcess()
    slow_handler.start()

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    try:
        server.serve_forever()
    except:
        slow_handler.running = False
        print 'Test'
