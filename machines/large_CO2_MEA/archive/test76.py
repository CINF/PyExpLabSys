
import json
import time
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
 
# To set a voltage on the pressure controller this is the message
message = 'json_wn#' + json.dumps({'A': 0.0, 'B': 0.0})

# If not
#message = 'json_wn#' + json.dumps({'no_voltages_to_set':True})

#message = b'name'
host = 'rasppi76'
port = 8500

t0 = time.time()
sock.sendto(message.encode('ascii'), (host, port)) 

# receive data from client (data, addr)
reply = sock.recv(1024).decode('ascii')
# The reply is prefixed with RET#, remove it and decode json
reply_data = json.loads(reply[4:])
#print(time.time() - t0)
#print(reply)
print('output from pressure controller: {}, output from voltage measurement: {}'.format(reply_data['1'],reply_data['3']))
