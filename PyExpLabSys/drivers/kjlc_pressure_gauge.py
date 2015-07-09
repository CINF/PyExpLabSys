import serial
import SocketServer
import time

KJLC = None

class KJLC300(object):
    """ Class the implements a KJLC interface """
    
    def __init__(self):
        self.connection = serial.Serial(0, baudrate=1200, bytesize=8,
                                        parity='N', stopbits=1, timeout=1,
                                        writeTimeout=1)

    def close(self):
        """ Closes connection """
        self.connection.close()

    def read_software_version(self):
        """ Reads software version """
        self.connection.write('#01VER\r')
        raw = self.connection.read(13)
        out = self._format_output(raw)
        return out

    def read_pressure(self):
        """ Reads pressure in Torr """
        self.connection.write('#01RD\r')
        raw = self.connection.read(13)
        out = self._format_output(raw)
        try:
            out = float(out)
            out = 1.33322 * out
            time.sleep(0.1)
        except ValueError:
            out = 'error'
        return out

    def _format_output(self, string):
        """ Strip *, the adress and a space from the beginning and a CR from the
        end
        """
        return string[4:-1]

class MyUDPHandler(SocketServer.BaseRequestHandler):
    """ UDP handler """

    def handle(self):
        recieved_data = self.request[0].strip()
        socket = self.request[1]

        if recieved_data.startswith('get'):
            data = KJLC.read_pressure()

        socket.sendto(str(data), self.client_address)

def main():
    global KJLC
    KJLC = KJLC300()
    
####    print KJLC.read_software_version()
##    print KJLC.read_pressure()
##    KJLC.close()

    host, port = 'localhost', 9990
    server = SocketServer.UDPServer((host, port), MyUDPHandler)
    try:
        print 'UPD server started. Press Ctrl-c to shut it down.'
        server.serve_forever()
    except KeyboardInterrupt:
        print 'UDP server closed. Shutting down seial interface.'
        KJLC.close()

if __name__ == '__main__':
    main()
