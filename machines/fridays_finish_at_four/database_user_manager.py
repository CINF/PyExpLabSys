#!/usr/bin/env python

"""Add new or modify existing users to database """

from bar_database import * # pylint: disable=wildcard-import,unused-wildcard-import
from nfc_reader import ThreadedNFCReader
import time

#class UserDatabase(object):
#    """Class for communicating with database (users)"""


DB = BarDatabase(host='servcinf-sql', port=3306)
# XXX the use of "with DB.connection:" works in MySQLdb.__version__ < 1.4.x

def show_user_list(user_id):
    with DB.connection:
        DB.cursor.execute("SELECT * FROM fridays_user WHERE id=%s",
                            (user_id,))
        row = DB.cursor.fetchall()
    if len(row) == 0:
        print('No user with id: ({})'.format(user_id))
        return
    print('For user id ({}):'.format(user_id))
    print('Credential, Name\n-----')
    for credential, name, user in row:
        print('{}, {}'.format(credential.decode('utf8'), name.decode('utf8')))
    print('-----')
    balance = DB.sum_log(user_id)
    print('-----')
    return

def is_credential_unique(user_barcode, print_output=True):
    """Check that barcode/credential doesn't already exist

    Return name and
    True if user_barcode unique
    else user_id using \'user_barcode\'"""
    with DB.connection:
        DB.cursor.execute("SELECT user_barcode, name, id FROM fridays_user WHERE user_barcode=%s",
                        (user_barcode,))
        row = DB.cursor.fetchall()
    if len(row) != 0:
        _, name, user_id = row[0]
        if print_output:
            print('User barcode already exists:')
            show_user_list(user_id)
        return name, user_id
    else:
        return '', True

def make_new_id(size=10000):
    # Get list of id's in database
    with DB.connection:
        DB.cursor.execute("SELECT id FROM fridays_user")
        row = DB.cursor.fetchall()
    list_of_ids = [int(x[0]) for x in row]
    next_id = min([x for x in range(size) if not x in list_of_ids])
    #print('Next unused id is {}'.format(next_id))
    return next_id

def insert_user(barcode='', name='', user_id=''):
    if len(barcode) == 0:
        print('No barcode given!')
        return False
    # Check barcode is unique
    _, unique = is_credential_unique(barcode, print_output=False)
    if unique is True:
        values = (barcode, name, user_id)
        with DB.connection:
            DB.cursor.execute("INSERT INTO fridays_user (user_barcode, name, id) "
                              "VALUES (%s, %s, %s)", values)
            row = DB.cursor.fetchall()
            print(row)
        return True
    else:
        print('Barcode {} already exists in user_id \'{}\'!'.format(repr(barcode), unique))
        return False

def make_deposit(user_id, user_barcode, transaction_type, amount):
    DB.insert_log(user_id, user_barcode, transaction_type, amount)
    #print(user_id, user_barcode, transaction_type, amount)
    balance = DB.sum_log(user_id)

if __name__ == '__main__':

    NFC = ThreadedNFCReader()
    NFC.start()

    while True:

        # Get input from user
        s = input('***\nSelect (q)uit, (n)ew user, (a)dd barcode to user,\n(d)eposit/(w)ithdraw money or (l)ist user\'s barcodes\n*** >>>')

        # Quit
        if s == 'q':
            NFC.close()
            exit()

        # List all selected user's current barcodes
        elif s == 'l':
            user_name = input('* Enter username (or user_id) >>>')

            if len(user_name) == 0 or user_name == 'q':
                continue

            # If user_id typed
            try:
                float(user_name)
                user_id = user_name

            except ValueError:
                # Get user_id and print list
                name, user_id = is_credential_unique(user_name, print_output=False)
                if user_id is True:
                    print('Username not detected.')
                    continue
            print('\nExisting accounts\n' + '_'*10)
            show_user_list(user_id)
            print('_'*10)

        # Add barcode to existing user
        elif s == 'a':
            user_name = input('* Which user should card be added to? >>>')

            if len(user_name) == 0 or user_name == 'q':
                continue

            name, user_id = is_credential_unique(user_name, print_output=False)
            if user_id is True:
                print('Username does not exist. If correctly typed, add a new user instead.\n')
                continue
            else:
                print('\nExisting accounts\n' + '_'*10)
                show_user_list(user_id)
                print('_'*10)
                while True:
                    s = input('* (t)ype barcode, (s)can smartcard, or <Enter> to go back >>>')

                    # Return
                    if len(s) == 0 or s == 'q':
                        break

                    # Typing mode
                    elif s == 't':
                        barcode = input('* Type barcode now >>>')
                        _, unique = is_credential_unique(barcode, print_output=False)
                        if unique is True:
                            ret = insert_user(name=name, barcode=barcode, user_id=user_id)
                            if ret:
                                print('Done.')
                        else:
                            print('Barcode {} already exists in user_id \'{}\'. Choose another or keyboard interrupt'.format(repr(barcode), unique))

                    # Smartcard mode
                    elif s == 's':
                        barcode = None
                        print('Ctrl+C to go back (keyboard interrupt)\n')
                        while True:
                            try:
                                barcode = NFC.last_item_in_queue
                                if barcode is None:
                                    time.sleep(0.5)
                                else:
                                    _, unique = is_credential_unique(barcode, print_output=False)
                                    if unique is True:
                                        #print((barcode, name, user_id)) # ADD USER HERE
                                        ret = insert_user(name=name, barcode=barcode, user_id=user_id)
                                        if ret:
                                            print('Done.')
                                        break
                                    else:
                                        print('Card {} already exists in user_id \'{}\'. Choose another or keyboard interrupt'.format(repr(barcode), unique))
                                        continue
                            except KeyboardInterrupt:
                                break

        # Add new user
        elif s == 'n':
            user_name = input('Type username (DTU initials or study number)\n>>>')

            # Return
            if len(user_name) == 0 or user_name.lower() == 'q':
                continue
            name, unique = is_credential_unique(user_name, print_output=False)
            if unique is True:
                new_id = make_new_id()
                name = input('Type your name >>>')
                msg = 'Please review input and accept/discard with "Y/n"\n(unique barcode, name, user id) = ({}, {}, {})\n'.format(user_name, name, new_id)
                accept = input(msg)
                if accept.lower() == 'y':
                    ret = insert_user(name=name, barcode=user_name, user_id=new_id)
                    if ret:
                        print('Done.')
                else:
                    print('Discarded. Try again.')
            else:
                print('Username already occupied by {} (id \'{}\')'.format(repr(name), unique))

        # Deposit money
        elif s == 'd' or s == 'w':
            if s == 'd':
                transaction_type = "deposit"
                msg = 'deposited for'
            elif s == 'w':
                transaction_type = "purchase"
                msg = 'withdrawn from'

            # Get user
            user_barcode = input('Whose user should money be {}? (DTU initials or study number)\n(leave empty to return)\n>>>'.format(msg))
            name, user_id = is_credential_unique(user_barcode, print_output=False)
            if user_id is True:
                print('Entered user_barcode doesn\'t exist.')
                continue

            # Get amount to deposit/withdraw
            amount = input('Enter deposit amount: ')
            try:
                amount = int(float(amount))
            except ValueError:
                print('Enter numbers only!')
                time.sleep(1)
                continue

            # Complete transaction
            make_deposit(user_id, user_barcode, transaction_type, amount)
            print('Transaction successful')
