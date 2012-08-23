import time
import socket
import sys

class NetworkComm():

    def __init__(self):
        self.host = "130.225.87.226"
        self.port = 9999

    def send_and_recieve(self,outgoing):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(outgoing + "\n", (self.host, self.port))
        incoming = sock.recv(1024)
        return incoming

    def string_to_usefull_data(self,string):
        return_dict = []
        for element in string.split(';'):
            return_dict.append(element.split('='))
        return_dict = dict(return_dict)
        return return_dict


    def usefull_data_to_string(self,usefull_data):
        string = ""
        for key,value in usefull_data.items():
            string = string + key + "=" + value + ";"
        return string[:-1]

    def network_sync(self,outgoing_dict):
        outgoing_string = self.usefull_data_to_string(outgoing_dict)
        incoming_string = self.send_and_recieve(outgoing_string)
        incoming_dict = self.string_to_usefull_data(incoming_string)
        return incoming_dict

if __name__ == "__main__":
    #a = time.time()

    test_dict = {'rtd_temperature': '23.5', 'power': '0.1'}

    network = NetworkComm()
    print network.network_sync(test_dict)
    #return_val = send_and_recieve("rtd_temperature=100;power=5.4")

    #print time.time()-a
