from sockets import GC_start_stop_socket
import time

gc = GC_start_stop_socket()

try:
    while True:
        print('still alive at '+time.ctime())
        time.sleep(5)
except KeyboardInterrupt:
    gc.stop()
