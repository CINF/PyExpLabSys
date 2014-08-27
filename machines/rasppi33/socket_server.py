""" Socket server for valve-control box """

import time
import SocketServer
import wiringpi2 as wp

class MyUDPHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        received_data = self.request[0].strip()
        data = "test"
        socket = self.request[1]

        if received_data == "read":
            print "read_all"
            data = ''
            for i in range(0, 20):
                data += str(wp.digitalRead(i))

        for i in range(0, 9):
            if (received_data[0:11] == "set_state_" + str(i + 1)):
                val = received_data[11:].strip()
                if val == '0':
                    wp.digitalWrite(i, 0)
                    data = "ok"
                if val == '1':
                    wp.digitalWrite(i, 1)
                    data = "ok"

        for i in range(9, 20):
            if (received_data[0:12] == "set_state_" + str(i + 1)):
                val = received_data[12:].strip()
                if val == '0':
                    wp.digitalWrite(i, 0)
                    data = "ok"
                if val == '1':
                    wp.digitalWrite(i, 1)
                    data = "ok"

        socket.sendto(data, self.client_address)

if __name__ == "__main__":
    wp.wiringPiSetup()

    time.sleep(1)

    for index in range(0, 21):  # Set GPIO pins to output
        wp.pinMode(index, 1)
        wp.digitalWrite(index, 0)

    # Now that all output are low, we can open main safety output
    wp.digitalWrite(20, 1)

    HOST, PORT = "10.54.7.33", 9999  # Rasppi33

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
