import time
import ParallelPortBinaryOut
import socket

def read_value(keyword):
    HOST, PORT = "127.0.0.1", 9999
    data = "read_" + keyword
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(data + "\n", (HOST, PORT))
    received = sock.recv(1024)
    temp = float(received)
    return temp

def control_temperature(setpoint):
    while True:
        temperature_outside = read_value("temperature_outside")
        temperature_1 = read_value("temperature_1")
        temperature_2 = read_value("temperature_2")
        print "Temperature outside: " + str(temperature_outside)
        print "Temperature 1: " + str(temperature_1)
        print "Temperature 2: " + str(temperature_2)
        if temperature_outside < setpoint:
            parallel.setState(0,True)
            time.sleep(5)
        else:
            parallel.setState(0,False)
            time.sleep(5)


if __name__ == "__main__":
   parallel = ParallelPortBinaryOut.ParallelPortBinaryOut()
   #parallel.setState(0,False)
   control_temperature(95)
