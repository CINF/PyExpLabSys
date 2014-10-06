import socket
import time

new_setpoint = 0
data = 'raw_wn#F25600004:float:' + str(new_setpoint)
host = '127.0.0.1'
port = 8500
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(0.2)
sock.sendto(data, (host, port))
received = sock.recv(1024)

new_setpoint = 0
data = 'raw_wn#F25600005:float:' + str(new_setpoint)
host = '127.0.0.1'
port = 8500
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(0.2)
sock.sendto(data, (host, port))
received = sock.recv(1024)


new_setpoint = 1
data = 'raw_wn#F25600005:float:' + str(new_setpoint)
host = '127.0.0.1'
port = 8500
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(0.2)
sock.sendto(data, (host, port))
received = sock.recv(1024)


new_setpoint = 1
data = 'raw_wn#F25600005:float:' + str(new_setpoint)
host = '127.0.0.1'
port = 8500
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(0.2)
sock.sendto(data, (host, port))
received = sock.recv(1024)
