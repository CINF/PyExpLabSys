""" Local channels for instruments directly connected """
import time
import threading
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.drivers.omega_D6400 import OmegaD6400
from PyExpLabSys.common.utilities import get_logger
from PyExpLabSys.common.utilities import activate_library_logging
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

LOGGER = get_logger('Local Mass Spec Channels', level='warning', file_log=True,
                    file_name='locals.txt', terminal_log=False,
                    email_on_warnings=False, email_on_errors=False,
                    file_max_bytes=104857600, file_backup_count=5)

activate_library_logging('PyExpLabSys.drivers.omega_D6400', logger_to_inherit_from=LOGGER)


class Local(threading.Thread):
    """ This class will be automatically started by the mass-spec program
    it can be arbritrarily simply or complex and will provide a local udp-socket
    to be included in a meta-channel in the mass-spec, thus allowing integraion
    of local instruments """
    def __init__(self):
        threading.Thread.__init__(self)
        #self.daemon = True
        self.pullsocket = DateDataPullSocket('local MS socket',
                                             ['analog_in'], timeouts=2, port=9250)
        self.pullsocket.start()
        port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWBEDQ3-if00-port0'
        self.omega = OmegaD6400(1, port=port)
        self.omega.update_range_and_function(2, action='voltage', fullrange='10')

    def run(self):
        while True:
            time.sleep(0.1)
            value = self.omega.read_value(2)
            self.pullsocket.set_point_now('analog_in', value)

def main():
    """ Main function """
    local_reader = Local()
    local_reader.start()

if __name__ == '__main__':
    main()
