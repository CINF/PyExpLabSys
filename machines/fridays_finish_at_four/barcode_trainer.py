#!/usr/bin/env python

"""Barcode scanner module"""

from bar_database import *  # pylint: disable=wildcard-import,unused-wildcard-import
from PyExpLabSys.drivers.vivo_technologies import BlockingBarcodeReader, detect_barcode_device


BAR_DATABASE = BarDatabase()


def read_barcode():
    """Read the barcode and return the number or None on error"""
    print 'Scan barcode now!'
    dev_ = detect_barcode_device()
    bbr = BlockingBarcodeReader(dev_)
    #bbr.start()
    line = bbr.read_barcode()

    out = int(line)
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
        data['barcode'] = read_barcode()
        message = 'type price: '
        data['price'] = input_with_type(message, int)
        message = 'type name of beer: '
        data['name'] = input_with_type(message, str)
        message = 'type alcohol precentage: '
        data['alc'] = input_with_type(message, float)
        message = 'type volume in liters: '
        data['volume'] = input_with_type(message, float)
    except ValueError:
        print 'Wrong input!... are you drunk?'
        return

    print data
    #bc.insert_item(data['barcode'], data['price'], data['name'], data['alc'], data['volume'])
    BAR_DATABASE.insert_item(**data)


def update():
    """Update an existing entry"""
    # Read data from database
    # select field to update
    # Read new value for this field
    # Update data base entry
    data = {}
    try:
        data['barcode'] = read_barcode()
        BAR_DATABASE.get_item(data['barcode'])
        message = 'state the field to update: '
        data['field'] = input_with_type(message, str)
        message_new = 'state the new value: '
        data['value'] = raw_input(message_new)
        BAR_DATABASE.replace_item(data['barcode'], data['field'], data['value'])
    except ValueError:
        print 'Wrong input!... are you drunk?'
        return

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
