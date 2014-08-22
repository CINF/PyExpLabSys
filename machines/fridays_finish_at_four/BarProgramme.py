#!/usr/bin/env python

"""Barcode scanner module"""

import sys
import os
import time
import subprocess
from BarCodeScanner import *
from PyExpLabSys.drivers.four_d_systems import PicasouLCD28PTU

bc = BeerClass()

for port in range(10):
    try:
        device = '/dev/ttyUSB{}'.format(port)
        picaso = PicasouLCD28PTU(serial_device=device, baudrate=9600)
        print picaso.get_spe_version()
    except:
        pass

sys.exit()

def read_barcode():
    """Read the barcode and return the number or None on error"""
    print 'Scan barcode now!'
    line = sys.stdin.readline().strip()
    os.system('clear')
    out = int(line)
    return out

def cowsay(text):
    p = subprocess.Popen(["cowsay", str(text)], stdout=subprocess.PIPE)
    out, err = p.communicate()
    
    return out

def run():
    """The main part of the program"""
    select = None
    data = {}
    while select != 'q':
        #message = "Enter (e)dit, (b)uy or (q)uit and press enter: "
        #select = raw_input(message)
        select = 'b'
        if select == 'b':
            try:
                data['barcode'] = read_barcode()
                print cowsay('Special price for you my friend (in DKK): \n' + str(bc.get_item(data['barcode'], statement='price')))
                time.sleep(3)
                os.system('clear')
                print cowsay('Enjoy your delicious ' + str(bc.get_item(data['barcode'], statement='name')))
                time.sleep(3)
                os.system('clear')
            except ValueError:
                print 'Wrong input!... are you drunk?'
                return
        elif select == 'u':
            update()
        


if __name__ == '__main__':
    run()
    #print cowsay('test test')
