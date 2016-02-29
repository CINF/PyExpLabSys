#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Barcode scanner module"""

import time
import textwrap
from bar_database import *  # pylint: disable=wildcard-import,unused-wildcard-import
from PyExpLabSys.drivers.four_d_systems import PicasouLCD28PTU, to_ascii_utf8
from serial.serialutil import SerialException
from PyExpLabSys.drivers.vivo_technologies import ThreadedBarcodeReader, detect_barcode_device
from ssh_tunnel import create_tunnel, close_tunnel, get_ip_address, test_demon_connection
from MySQLdb import OperationalError
from cowsay import Cowsay


__version__ = 2.317
COWSAY = Cowsay(cow='cow', width=34)


def cowsay(text):
    """Display text in Cowsay manner"""
    return COWSAY.say_get_string(text)


class NewBarcode(Exception):
    """Custom exception used to signal that a new barcode has been received"""
    def __init__(self, barcode):
        self.barcode = barcode
        super(NewBarcode, self).__init__()


class Bar101(object):
    """Barcodescanner programme class """
    def __init__(self):
        # Initialize internal variables
        self.tbs = None
        self.bar_database = None
        # Setup of display
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
                print "Barcode: ", repr(barcode)
                raise NewBarcode(barcode)

    def start_up(self):
        """Starting up initials"""
        self.picaso.clear_screen()

        # Testing demon connection
        attempt_number = 0
        while not test_demon_connection():
            self.picaso.move_cursor(2, 0)
            attempt_number += 1
            status_string = "Demon connection attempt {} failed".format(attempt_number)
            self.picaso.put_string(status_string)
            time.sleep(1)

        # Demon connection successful
        self.picaso.clear_screen()
        self.picaso.move_cursor(2, 0)
        status_string = "Demon connection attempt succeeded".format(attempt_number)
        self.picaso.put_string(status_string)

        # Create ssh tunnel
        self.picaso.move_cursor(3, 0)
        if create_tunnel():
            self.picaso.put_string('Created SSH tunnel')
        else:
            self.picaso.put_string('Unable to create SSH tunnel. Quitting!')
            time.sleep(5)
            raise SystemExit('Unable to create ssh tunnel')

        # Print network interface and ip address
        interface, ip_address = get_ip_address()
        self.picaso.move_cursor(5, 0)
        interface_string = "Interface: {}".format(interface)
        self.picaso.put_string(interface_string)
        self.picaso.move_cursor(6, 0)
        ip_address_string = "Ip address: {}".format(ip_address)
        self.picaso.put_string(ip_address_string)

        # Start the database backend
        time.sleep(1)
        for _ in range(10):
            try:
                self.bar_database = BarDatabase('127.0.0.1', 9000)
                break
            except OperationalError:
                time.sleep(1)
        self.picaso.move_cursor(7, 0)
        self.picaso.put_string('Connection to database')

        # Start barcode scanner
        dev_ = detect_barcode_device()
        print dev_
        self.tbs = ThreadedBarcodeReader(dev_)
        self.tbs.start()
        time.sleep(1)

    def clean_up(self):
        """Closing down"""
        self.tbs.close()
        print 'cleaning up'
        time.sleep(1)

    def query_barcode(self):
        """Initial message"""
        self.picaso.clear_screen()
        self.picaso.move_cursor(1, 0)
        self.picaso.put_string(cowsay("Welcome to the Friday Bar. Please scan your barcode!"))
        self.picaso.move_cursor(19, 0)
        self.picaso.put_string("Friday Bar System Version {:.3f}".format(__version__))
        self.timer(None)

    def present_beer(self, barcode):
        """INSERT Show beer"""
        self.picaso.clear_screen()
        beer_price = str(self.bar_database.get_item(barcode, statement='price'))
        self.picaso.move_cursor(4, 4)
        self.picaso.put_string("Special price for you my friend:")
        self.picaso.move_cursor(7, 5)
        self.picaso.text_factor(5)
        self.picaso.put_string("{} DKK".format(beer_price))

        self.timer(3)
        # INSERT Show spiffy comment
        self.picaso.clear_screen()
        self.picaso.move_cursor(1, 0)
        self.picaso.put_string(cowsay("Enjoy your delicious {}".format(
            to_ascii_utf8(self.bar_database.get_item(barcode, statement='name'))
        )))
        self.timer(4)

    def present_insult(self):
        """Presents insult if programme handled wrong"""
        self.picaso.clear_screen()
        self.picaso.move_cursor(1, 0)
        self.picaso.put_string(cowsay("You did it all wrong! Time to go home?"))
        self.timer(2)

    def purchase_beer(self, beer_barcode, user_barcode):
        """User purchases beer"""
        beer_price = self.bar_database.get_item(beer_barcode, statement='price')
        user_name, user_id = self.bar_database.get_user(user_barcode)
        user_name = to_ascii_utf8(user_name)
        if beer_price <= self.bar_database.sum_log(user_id):
            # Since the beer_barcode may be both the real barcode or the alternative
            # barcode we need to get the real barcode from the db for the transactions log
            real_beer_barcode = int(self.bar_database.get_item(beer_barcode, statement='barcode'))
            self.bar_database.insert_log(user_id, user_barcode, "purchase", beer_price,
                                         item=real_beer_barcode)
            beer_name = self.bar_database.get_item(beer_barcode, statement='name')
            beer_name = to_ascii_utf8(beer_name)
            balance = self.bar_database.sum_log(user_id)

            self.picaso.clear_screen()
            self.picaso.move_cursor(1, 0)
            self.picaso.put_string("User: {}".format(user_name))
            self.picaso.move_cursor(3, 0)
            self.picaso.put_string("Beer purchased:")
            self.picaso.move_cursor(4, 0)
            self.picaso.text_factor(2)
            self.picaso.put_string("{}".format(beer_name))
            self.picaso.move_cursor(5, 0)
            self.picaso.text_factor(1)
            self.picaso.put_string("Account balance: {}".format(balance))
            self.timer(3)
        else:
            self.picaso.clear_screen()
            x_screen_resolution = self.picaso.get_graphics_parameters('x_max')
            y_screen_resolution = self.picaso.get_graphics_parameters('y_max')
            self.picaso.draw_filled_rectangle(
                (0, 0), (x_screen_resolution, y_screen_resolution), (1, 0, 0)
            )
            self.picaso.move_cursor(1, 0)
            self.picaso.text_factor(3)
            self.picaso.text_foreground_color((0, 0, 0))
            self.picaso.text_background_color((1, 0, 0))
            self.picaso.put_string("Insufficient")
            self.picaso.move_cursor(2, 0)
            self.picaso.put_string("Funds!")
            self.picaso.move_cursor(4, 0)
            self.picaso.text_factor(2)
            self.picaso.put_string("Get a job")
            self.picaso.text_foreground_color((0, 1, 0))
            self.picaso.text_background_color((0, 0, 0))
            self.timer(5)

    def make_deposit(self, user_barcode, amount):
        """User deposits money to user account"""
        amount = int(amount)
        _, user_id = self.bar_database.get_user(user_barcode)
        self.bar_database.insert_log(user_id, user_barcode, "deposit", amount)
        balance = self.bar_database.sum_log(user_id)

        self.picaso.clear_screen()
        self.picaso.move_cursor(1, 10)
        self.picaso.put_string("You have deposited:")
        self.picaso.move_cursor(7, 5)
        self.picaso.text_factor(5)
        self.picaso.put_string("{} DKK".format(amount))
        self.picaso.text_factor(1)
        self.picaso.move_cursor(14, 8)
        self.picaso.put_string("Balance: {} DKK".format(balance))
        self.timer(3)

    def present_user(self, user_barcode):
        """Present user info, i.e. user name and balance"""
        user_name, user_id = self.bar_database.get_user(user_barcode)
        user_name = to_ascii_utf8(user_name)
        balance = self.bar_database.sum_log(user_id)
        # Screen layout, username
        self.picaso.clear_screen()
        #self.picaso.move_cursor(1, 0)
        self.picaso.move_origin(0, 5)
        self.picaso.put_string("User:")
        # Wrap names to 20 characters and display two lines
        name_lines = textwrap.wrap(user_name, 20)
        self.picaso.text_factor(2)
        self.picaso.move_cursor(1, 0)
        self.picaso.put_string(name_lines[0])
        if len(name_lines) > 1:
            self.picaso.move_cursor(2, 0)
            self.picaso.put_string(name_lines[1])
        # Balance
        self.picaso.text_factor(1)
        self.picaso.move_cursor(7, 0)
        self.picaso.put_string("Balance:")
        self.picaso.text_factor(3)
        self.picaso.move_cursor(3, 0)
        self.picaso.put_string("{}".format(balance))
        # Timeout
        for number in range(10, 0, -1):
            self.picaso.move_cursor(5, 0)
            self.picaso.put_string("Timeout: {: <2} ".format(number))
            self.timer(1)

    def run(self):
        """Main method"""
        # action is a reference to the method that will be called next, kwargs is its
        # arguments
        action = self.query_barcode
        kwargs = {}
        while True:
            try:
                # Call the pending action, if this action returns, the action it was
                # supposed to do, timed out, without getting a new barcode and so we make
                # the next action "query_barcode"
                action(**kwargs)
                old_action = action
                old_kwargs = kwargs
                # No new barcode recieved
                action = self.query_barcode
                kwargs = {}

            # We received a new barcode during the previous action
            except NewBarcode as new_barcode:
                old_action = action
                old_kwargs = kwargs
                barcode_type = self.bar_database.get_type(new_barcode.barcode)
                # Default to query_barcode
                action = self.query_barcode
                kwargs = {}
                if barcode_type == 'beer':
                    if old_action == self.present_user:
                        action = self.purchase_beer
                        kwargs = {
                            'beer_barcode': new_barcode.barcode,
                            'user_barcode': old_kwargs['user_barcode'],
                        }
                    else:
                        action = self.present_beer
                        kwargs = {'barcode': new_barcode.barcode}
                elif barcode_type == 'user':
                    action = self.present_user
                    kwargs = {'user_barcode': new_barcode.barcode}
                elif barcode_type == 'deposit_amount':
                    if old_action == self.present_user:
                        action = self.make_deposit
                        kwargs = {
                            'amount': new_barcode.barcode,
                            'user_barcode': old_kwargs['user_barcode'],
                        }
                elif barcode_type == 'invalid':
                    action = self.present_insult
                    kwargs = {}


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
            close_tunnel()
            break
        except:
            bar101.clean_up()
            close_tunnel()
            raise

    close_tunnel()

if __name__ == '__main__':
    main()
