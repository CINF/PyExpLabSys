#!/usr/bin/env python

"""Barcode scanner module"""
# Run sudo chmod o+rw /dev/input/event*

import sys
from bar_database import *
from PyExpLabSys.drivers.vivo_technologies import BlockingLS689A, detect_barcode_device


bar_database = BarDatabase(host='servcinf-sql', port=3306)


def read_barcode():
    """Read the barcode and return the number or None on error"""
    print 'Scan barcode now!'
    #import StringIO
    #s = StringIO.StringIO()
    #old_stdin = sys.stdin
    #sys.stdin = s
    #dev_ = detect_barcode_device()
    #bbr = BlockingLS689A(dev_)
    #bbr.start()
    #line = bbr.read_barcode()
    line = raw_input()

    out = int(line)
    #sys.stdin = old_stdin
    return out


def new():
    """Create a new entry"""
    # Read barcode
    # Check that entry does not exist in data base
    # Read price
    # Read name
    # Read line 2 (funny note)
    # Confirm information
    # Send to data base
    data = {}
    try:
        data['user_id'] = read_barcode()
        message = 'Type user name: '
        data['name'] = input_with_type(message, str)
    except ValueError:
        print 'Wrong input!... are you drunk?'
        return
    
    print data
    bar_database.insert_user(**data)
    

def input_with_type(prompt, type_function):
    '''Read input from raw input and type convert'''
    out = raw_input(prompt)
    out = type_function(out)
    
    return out


def run():
    """The main part of the program"""
    select = None
    while select != 'q':
        message = "Enter (n)ew, (u)pdate or (q)uit and press enter: "
        select = raw_input(message)
        if select == 'n':
            new()
        elif select == 'u':
            update()


if __name__ == '__main__':
    run()
