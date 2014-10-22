import time
import wiringpi2 as wp
import sys
sys.path.insert(1, '/home/pi/PyExpLabSys')
from PyExpLabSys.common.sockets import DateDataPullSocket


name = 'stm312 xps water flow'
codenames = ['water_flow']
socket = DateDataPullSocket(name, codenames)


wp.wiringPiSetup()
for i in range(0, 7): #Set GPIO pins to output
    wp.pinMode(i, 0)
def main():
    while True:
        now = wp.digitalRead(0)
        counter = 0
        counter_same = 0
        t = time.time()
        for i in range(0,1000):
            new = wp.digitalRead(0)
            if now != new:
                counter += 1
                now = new
            else:
                counter_same += 1
            time.sleep(0.0001)
        freq = 0.5 * counter / (time.time() - t)
        water_flow = freq*60./6900
        print 'freq: ' + str(freq) + ' , integration time: ' + str(time.time() - t) + ', L/min: ' + str(water_flow) + ', ident: ' + str(float(counter)/counter_same)
        socket.set_point_now('water_flow',water_flow)

if __name__ == "__main__":
    socket.start()
    try:
        main()
    except KeyboardInterrupt:
        socket.stop()

