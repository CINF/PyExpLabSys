import time
import socket
import sys

from subprocess import call

a = time.time()

#HOST, PORT = "localhost", 9999
#HOST, PORT = "130.225.87.189", 9999 #Kenneth
#HOST, PORT = "130.225.87.191", 9999 #robertj
#HOST, PORT = "130.225.86.242", 9999 #thomas
#HOST, PORT = "130.225.87.226", 9999 #robertj
HOST, PORT = "130.225.87.213", 9999 #rasppi04
data = " ".join(sys.argv[1:])

# SOCK_DGRAM is the socket type to use for UDP sockets
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# As you can see, there is no connect() call; UDP has no connections.
# Instead, data is directly sent to the recipient via sendto().
sock.sendto(data + "\n", (HOST, PORT))
#sock.sendto(data, (HOST, PORT))
received = sock.recv(1024)

print "Sent:     {}".format(data)
#print "Received: {}".format(received)

print received

call(["wget", received])

print time.time()-a
