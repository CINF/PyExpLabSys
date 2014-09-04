#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Barcode scanner module"""

import sys
import os
import time
import subprocess
from bar_database import *
from PyExpLabSys.drivers.four_d_systems import PicasouLCD28PTU, to_ascii
from serial.serialutil import SerialException
from PyExpLabSys.drivers.vivo_technologies import ThreadedLS689A, detect_barcode_device
from ssh_tunnel import create_tunnel, close_tunnel, get_ip_address, test_demon_connection


__version__ = 1.000
#bar_database = BarDatabase()
#bar_database = None


def cowsay(text):
    """Display text in Cowsay manner"""
    p = subprocess.Popen(["/usr/games/cowsay", "-ftux", "-W34", str(text)], stdout=subprocess.PIPE)
    out, err = p.communicate()
    return out


class NewBarcode(Exception):
    """Custom exception used to signal that a new barcode has been received"""
    def __init__(self, barcode):
        self.barcode = barcode
        super(NewBarcode, self).__init__()


class Bar101(object):
    """Barcodescanner programme class """
    def __init__(self):
        #Initialize internal variables
        self.tbs = None
        self.bar_database = None
        #Setup of display
        for port in range(8):
            try:
                device = '/dev/ttyUSB{}'.format(port)
                picaso = PicasouLCD28PTU(serial_device=device, baudrate=9600)
                spe_version = picaso.get_spe_version()
                picaso.screen_mode('landscape reverse')
                if spe_version == '1.2':
                    self.picaso = picaso
                    break
            except SerialException:
                pass


    def timer(self, timeout=3):
        """Set timeout to None to run forever"""
        while timeout is None or timeout > 0:
            time.sleep(0.1)
            if timeout is not None:
                timeout -= 0.1
            barcode = self.tbs.last_barcode_in_queue
            if barcode is not None:
                raise NewBarcode(barcode)

    def start_up(self):
        """Starting up initials"""
        self.picaso.clear_screen()

        #testing demon connection
        attempt_number = 0
        while not test_demon_connection():
            self.picaso.move_cursor(0, 0)
            attempt_number += 1
            status_string = "Demon connection attempt {} failed".format(attempt_number)
            self.picaso.put_string(status_string)
        self.picaso.clear_screen()
        status_string = "Demon connection attempt succeeded".format(attempt_number)
        self.picaso.put_string(status_string)

        # Print network interface and ip address
        interface, ip_address = get_ip_address()
        self.picaso.move_cursor(2, 0)
        interface_string = "Interface: {}".format(interface)
        self.picaso.put_string(interface_string)
        self.picaso.move_cursor(3, 0)
        ip_address_string = "Ip address: {}".format(ip_address)
        self.picaso.put_string(ip_address_string)

        # Start the database backend
        self.bar_database = BarDatabase()

        #Start barcode scanner
        dev_ = detect_barcode_device()
        print dev_
        self.tbs = ThreadedLS689A(dev_)
        self.tbs.start()
        time.sleep(2)

    def clean_up(self):
        """Closing down"""
        self.tbs.close()
        print 'cleaning up'
        time.sleep(1)

    def query_barcode(self):
        """Initial message"""
        self.picaso.clear_screen()
        self.picaso.put_string(cowsay("Welcome to the Friday Bar. Please scan your barcode!"))
        self.picaso.move_cursor(19, 0)
        self.picaso.put_string("Friday Bar System Version {}".format(__version__))
        self.timer(None)

    def present_beer(self, barcode):
        # INSERT Show beer
        import time
        self.picaso.clear_screen()
        t0 = time.time()
        beer_price = str(self.bar_database.get_item(barcode, statement='price'))
        print "database", time.time() - t0
        cowsay_string = cowsay("Special price for you my friend: " + beer_price + " DKK")
        print "cowsay", time.time() - t0
        self.picaso.put_string(cowsay_string)
        print "put string", time.time() - t0

        self.timer(3)
        # INSERT Show spiffy comment
        self.picaso.clear_screen()
        self.picaso.put_string(cowsay("Enjoy your delicious " + str(self.bar_database.get_item(barcode, statement='name'))))
        self.timer(4)

    def present_insult(self):
        """Presents insult if programme handled wrong"""
        self.picaso.clear_screen()
        self.picaso.put_string(cowsay("You did it all wrong! Time to go home?"))
        self.timer(2)

    def run(self):
        action, args = self.query_barcode, {}
        while True:
            try:
                action(**args)
                action, args = self.query_barcode, {}
            except NewBarcode as new_barcode:
                barcode_type = self.bar_database.get_type(new_barcode.barcode)
                if barcode_type == 'beer':
                    action = self.present_beer
                    args = {'barcode': new_barcode.barcode}
                elif barcode_type == 'invalid':
                    action, args = self.present_insult, {}


def main():
    """Main function"""
    bar101 = Bar101()
    while True:
        bar101.start_up()
        try:
            bar101.run()
        except KeyboardInterrupt:
            bar101.clean_up()
            bar101.picaso.close()
            break
        except:
            bar101.clean_up()
            raise

if __name__ == '__main__':
    main()
