""" Read voltages from the Time-of-Flight and expose to network """
from __future__ import print_function
import SocketServer
import threading
import time
import PyExpLabSys.drivers.agilent_34972A as multiplexer
import read_tof_voltages

class SlowProcess(threading.Thread):
    """ Perfom a slow operation without blocking the network """
    def __init__(self):
        threading.Thread.__init__(self)
        self.bias_values = {}
        self.update = False
        self.running = True
        self.recent_update = -1

    def update_bias_string(self):
        """ Call helper to update actual voltages """
        self.bias_values = read_tof_voltages.read_voltages()

    def run(self):
        while self.running:
            if self.update: # Force an update of bias values
                self.update_bias_string()
                time.sleep(0.1)
                self.recent_update = 20
                self.update = False
            else:
                self.recent_update = self.recent_update - 1
                time.sleep(1)
            if self.recent_update < 0: # If not updated recently, do not trust store values
                self.bias_string = {}


class MyUDPHandler(SocketServer.BaseRequestHandler):
    """ Handle request to read or update store bias values """
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
            print(string)
            slow_handler.update = True
            data = 'ok'

        command = 'read_voltages'
        if recieved_data[0:len(command)] == command:
            print('read voltages')
            data_values = slow_handler.bias_values
            data = ''
            for key in data_values.keys():
                data += key + ':' + str(data_values[key]) + ' '
            print(data)

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
            print(val)
            print('set_bias')

        command = 'aps' #Ask pause status
        if recieved_data[0:len(command)] == command:
            data = str(slow_handler.update)
            print(data)

        socket.sendto(data, self.client_address)


if __name__ == "__main__":
    host, port = '10.54.7.74', 9696 # rasppi74

    bias = -1
    pec = False
    agilent = multiplexer.Agilent34972ADriver(hostname='tof-agilent-34972a')

    slow_handler = SlowProcess()
    slow_handler.start()

    server = SocketServer.UDPServer((host, port), MyUDPHandler)
    try:
        server.serve_forever()
    except:
        slow_handler.running = False
        print('Test')
