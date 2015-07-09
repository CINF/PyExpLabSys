import serial
import time

KJLC = None

class KJLC300(object):
    """ Class the implements a KJLC interface """
    
    def __init__(self, port):
        self.connection = serial.Serial(port, baudrate=1200, bytesize=8,
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

