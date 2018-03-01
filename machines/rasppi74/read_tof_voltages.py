""" Read the voltages from the analog voltage supply for the TOF """
from __future__ import print_function
import socket
import PyExpLabSys.drivers.agilent_34972A as multiplexer
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

def read_network(command):
    """ Read value from network """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1)
    sock.sendto(command, ('127.0.0.1', 9000))
    received = sock.recv(1024).decode()
    data = float(received[received.find(',') + 1:])
    return data

def read_voltages():
    """ Do the reading """
    mux = multiplexer.Agilent34972ADriver(hostname='tof-agilent-34972a')
    mux.set_scan_list(['106,107,108,109,110,111,112,115'])

    values = mux.read_single_scan()

    return_values = {}
    return_values['a2'] = values[6] * 10 / 0.9911
    return_values['deflection'] = values[3] * 1000 / 0.9936
    return_values['focus'] = values[2]  * 1000 / 0.9925
    return_values['liner'] = values[1]  * 1000 / 0.9938
    return_values['mcp'] = values[0]  * 1000 / 0.9943
    return_values['r1'] = values[4]  * 1000 / 0.9931
    return_values['r2'] = values[5] * 1000 / 0.9875
    return_values['lens_A'] = read_network(b'lens_a#raw')
    return_values['lens_B'] = read_network(b'lens_b#raw')
    return_values['lens_C'] = read_network(b'lens_c#raw')
    return_values['lens_D'] = read_network(b'lens_d#raw')
    return_values['lens_E'] = read_network(b'lens_e#raw')
    return_values['deflection'] = values[7] * 500
    return return_values

if __name__ == '__main__':
    print(read_voltages())
