#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Barcode scanner module"""

import sys
import os
import time
import subprocess
from BarCodeScanner import *
from PyExpLabSys.drivers.four_d_systems import PicasouLCD28PTU
from serial.serialutil import SerialException

__version__ = 0.002

latin_dict = {
    u"¡": u"!", u"¢": u"c", u"£": u"L", u"¤": u"o", u"¥": u"Y",
    u"¦": u"|", u"§": u"S", u"¨": u"`", u"©": u"c", u"ª": u"a",
    u"«": u"<<", u"¬": u"-", u"­": u"-", u"®": u"R", u"¯": u"-",
    u"°": u"o", u"±": u"+-", u"²": u"2", u"³": u"3", u"´": u"'",
    u"µ": u"u", u"¶": u"P", u"·": u".", u"¸": u",", u"¹": u"1",
    u"º": u"o", u"»": u">>", u"¼": u"1/4", u"½": u"1/2", u"¾": u"3/4",
    u"¿": u"?", u"À": u"A", u"Á": u"A", u"Â": u"A", u"Ã": u"A",
    u"Ä": u"A", u"Å": u"Aa", u"Æ": u"Ae", u"Ç": u"C", u"È": u"E",
    u"É": u"E", u"Ê": u"E", u"Ë": u"E", u"Ì": u"I", u"Í": u"I",
    u"Î": u"I", u"Ï": u"I", u"Ð": u"D", u"Ñ": u"N", u"Ò": u"O",
    u"Ó": u"O", u"Ô": u"O", u"Õ": u"O", u"Ö": u"O", u"×": u"*",
    u"Ø": u"Oe", u"Ù": u"U", u"Ú": u"U", u"Û": u"U", u"Ü": u"U",
    u"Ý": u"Y", u"Þ": u"p", u"ß": u"b", u"à": u"a", u"á": u"a",
    u"â": u"a", u"ã": u"a", u"ä": u"a", u"å": u"aa", u"æ": u"ae",
    u"ç": u"c", u"è": u"e", u"é": u"e", u"ê": u"e", u"ë": u"e",
    u"ì": u"i", u"í": u"i", u"î": u"i", u"ï": u"i", u"ð": u"d",
    u"ñ": u"n", u"ò": u"o", u"ó": u"o", u"ô": u"o", u"õ": u"o",
    u"ö": u"o", u"÷": u"/", u"ø": u"oe", u"ù": u"u", u"ú": u"u",
    u"û": u"u", u"ü": u"u", u"ý": u"y", u"þ": u"p", u"ÿ": u"y", 
    u"’":u"'"
}


bc = BeerClass()


for port in range(8):
    try:
        device = '/dev/ttyUSB{}'.format(port)
        #print device
        picaso = PicasouLCD28PTU(serial_device=device, baudrate=9600)
        spe_version = picaso.get_spe_version()
        picaso.screen_mode('landscape reverse')
        if spe_version == '1.2':
            break
    except SerialException:
        pass

def read_barcode():
    """Read the barcode and return the number or None on error"""
    print 'Scan barcode now!'
    line = sys.stdin.readline().strip()
    os.system('clear')
    out = int(line)
    return out

def cowsay(text):
    p = subprocess.Popen(["cowsay", "-W34", str(text)], stdout=subprocess.PIPE)
    out, err = p.communicate()
    
    return out

def print_to_screen():
    picaso.put_string()
    return

def to_ascii(string):
    for char in string:
        if char in latin_dict:
            string = string.replace(char,latin_dict[char])
    return string

def run():
    """The main part of the program"""
    select = None
    data = {}
    picaso.text_foreground_color((1, 1, 1))
    while select != 'q':
        #message = "Enter (e)dit, (b)uy or (q)uit and press enter: "
        #select = raw_input(message)
        select = 'b'
        if select == 'b':
            try:
                picaso.clear_screen()
                picaso.put_string("Welcome to the Friday Bar!")
                picaso.move_cursor(1, 0)
                picaso.put_string("Friday Bar System Version {}".format(__version__))
                picaso.move_cursor(4, 0)
                picaso.put_string('Scan your barcode!')
                data['barcode'] = read_barcode()
                #print cowsay('Special price for you my friend (in DKK): \n' + str(bc.get_item(data['barcode'], statement='price')))
                picaso.clear_screen()
                #picaso.put_string('Special price for you my friend: \n' + str(bc.get_item(data['barcode'], statement='price')) + ' DKK')
                try:
                    picaso.put_string(cowsay('Special price for you my friend: \n' + str(bc.get_item(data['barcode'], statement='price')) + ' DKK'))
                except:
                    picaso.put_string(cowsay('Invalid barcode! Are you drunk?'))
                    time.sleep(3)
                    continue
                
                time.sleep(3)
                picaso.clear_screen()
                #os.system('clear')
                name = bc.get_item(data['barcode'], statement='name').decode('utf-8')
                picaso.put_string(cowsay('Enjoy your delicious ' + to_ascii(name)))
                time.sleep(2)
                #time.sleep(3)
                #os.system('clear')
            except IOError:##ValueError:
                print 'Wrong input!... are you drunk?'
                return
        elif select == 'u':
            update()
        


if __name__ == '__main__':
    run()
    #print cowsay('test test')
