"""\"Driver\" for NFC reader model ACR122U

Manual referred to (available from acs webpage):
------------
ACR122U Application Programming Interface V2.04
URL: XXXX
------------

Notes on installing pyscard on raspberry pi (steps taken this round):

1.
" sudo apt-get install pcscd pcsc-tools "
status: success

2.
" sudo pip install pyscard "
status: failed
(swig error)

3.
" python -m pip install --upgrade pip setuptools wheel "
status: Successfully installed pip-10.0.1 setuptools-39.2.0 wheel-0.31.1

4.
" pip --version "
status: pip 9.0.1 from /usr/lib/python2.7/dist-packages (python2.7)

5.
" pip3 --version "
status: ImportError: cannot import name 'main' (from pip import main - in /usr/bin/pip3)

6.
" sudo apt-get install swig "
status: Completed

7.
" sudo apt-get install python3-pyscard "
status: Completed

-----------
"""

import threading
import time
try:
    import Queue
except ImportError:
    import queue as Queue

# pyscard imports:
from smartcard.System import readers
from smartcard.CardType import ATRCardType
from smartcard.CardRequest import CardRequest
from smartcard.util import toHexString, toBytes
from smartcard.Exceptions import CardRequestTimeoutException, CardConnectionException

def convert_response(response):
    """Crude conveniency function.
Get response as hex string from returned bytes """
    ID = ''
    for byte in response:
        last_part = hex(byte)[2:]
        if len(last_part) < 2: # append zero, if neglected
            ID += '0'
        ID += last_part
    return ID

def load_database(filename):
    """Open file FILENAME to read database contents. Return as dict """
    
    try:
        f = open(filename, 'r')
        contents = f.readlines()
        f.close()
    except FileNotFoundError:
        f = open(filename, 'w')
        f.close()
        return dict()

    database = dict()
    for line in contents:
        content = line.rstrip('\r\n').split(';;')
        database[content[0]] = content[1]
    return database

def update_database(filename, database):
    """Writes dict database to file FILENAME 
        dict : (key, value) = (ID, description)"""

    f = open(filename, 'w')
    string = '{};;{}\r\n'
    for (key, value) in database.items():
        f.write(string.format(key, value))
    f.close()

class ThreadedNFCReader(threading.Thread):
    """Threaded NFC/RFID reader that holds only the last value"""

    def __init__(self):
        # Initialize thread
        super(ThreadedNFCReader, self).__init__()
    
        # Detect smart card readers
        self.readers = readers()
        for reader in self.readers:
            if 'ACS ACR122U' in reader.name:
                print('ACS ACR122U NFC reader detected!')
        if len(self.readers) > 1 or len(self.readers) == 0:
            print('None or more readers detected!')
            print('Reader list: ', self.readers)
        self.active = False

        # Only look for Mifare Classic 4k type cards (Rejsekort/Studiekort)
        self.cardtype = ATRCardType( toBytes( "3B 8F 80 01 80 4F 0C A0 00 00 03 06 03 00 02 00 00 00 00 69" ) )
        self.cardrequest = CardRequest( timeout=1, cardType=self.cardtype )
        self.apdu = {'UID': [0xFF, 0xCA, 0x00, 0x00, 0x00], # Manual Section 4.1, p.11
                    }

        # Initialize constants
        self.daemon = True
        self._detection_queue = Queue.Queue()
        self.new_card = True
        self.stop = False

    def run(self):
        """The threaded run method"""

        self.active = True
        while not self.stop:
            try:
                time.sleep(0.1)
                # Wait for card
                cardservice = self.cardrequest.waitforcard()

                # No TimeoutException means that a card is found.
                cardservice.connection.connect()

                # Don't react if card is left in reader
                if self.new_card:
                    # Get user id of card
                    UID, sw1, sw2 = cardservice.connection.transmit(self.apdu['UID'])
                    print(UID, sw1, sw2)
                    self._detection_queue.put( convert_response(UID) )
                    self.new_card = False

                cardservice.connection.disconnect()

            except CardRequestTimeoutException:
                self.new_card = True
            except CardConnectionException as e:
                self.new_card = True
                print(e)
            except Exception as e:
                print('Card loop exception:')
                print('Error message: {}'.format(e))
                print('Readers loaded: {}'.format(self.readers))
                print('Readers detected: {}'.format(readers()))
                raise

    @property
    def last_item_in_queue(self):
        """Last detection in queue"""
        last = None
        while True:
            try:
                last = self._detection_queue.get_nowait()
            except Queue.Empty:
                break
        return last

    def close(self):
        """Stop event loop and kill thread"""
        self.stop = True

if __name__ == '__main__':
    #DATABASE_NAME = 'test_database.dscsv'
    #database = load_database(DATABASE_NAME)

    NFC = ThreadedNFCReader()
    NFC.daemon = False
    NFC.start()

    while True:
        try:
            time.sleep(0.1)
            UID = NFC.last_item_in_queue
            print(UID)
            if UID is not None:
                #if UID in database.keys():
                #    print('card identified ({}): {}'.format(UID, database[UID]))
                #else:
                #    print('new card found: ({})'.format(UID))
                print('User ID detected: {}'.format(UID))
            else:
                continue
        except KeyboardInterrupt:
            NFC.close()
            break
