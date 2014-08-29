import time
import wiringpi2 as wp


wp.wiringPiSetup()

for i in range(0, 7): #Set GPIO pins to output
    wp.pinMode(i, 0)

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
    print 'freq: ' + str(freq) + ' , integration time: ' + str(time.time() - t) + ', L/min: ' + str(freq*60/6900.0) + ', ident: ' + str(float(counter)/counter_same)
