import time
import wiringpi2 as wp


if __name__ == '__main__':
    wp.wiringPiSetup()

    time.sleep(1)

    for i in range(0, 20): #Set GPIO pins to output
        wp.pinMode(i, 1)
        wp.digitalWrite(i, 0)

    time.sleep(1)
    wp.digitalWrite(1, 1)

    time.sleep(5)
    wp.digitalWrite(1, 0)

