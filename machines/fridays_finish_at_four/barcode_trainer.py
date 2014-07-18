#!/usr/bin/env python

"""Barcode scanner module"""

import sys


def read_barcode():
    """Read the barcode and return the number or None on error"""
    print 'Scan barcode now!'
    line = sys.stdin.readline().strip()

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
    except ValueError:
        print 'Wrong input!... are you drunk?'
        return
    
    print data


def update():
    """Update an existing entry"""
    # Read data from database
    # select field to update
    # Read new value for this field
    # Update data base entry
    pass
    
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
