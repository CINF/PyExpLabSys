"""Driver for a Vivo Technologies LS-689A barcode scanner"""

import glob
import evdev
import threading
import time

try:
    import Queue
except ImportError:
    import queue as Queue


def detect_barcode_device():
    """Return the input device path of the Barcode Scanner

    Iterates over all devices in /dev/input/event?? and looks for one that has
    'Barcode Reader' in its description.

    Returns:
        str: The Barcode Scanner device path
    """
    barcode_device = None
    for device_string in glob.glob("/dev/input/event*"):
        try:
            tmp_dev = evdev.InputDevice(device_string)
        except OSError:
            continue
        else:
            device_description = str(tmp_dev)
            tmp_dev.close()

        if "Barcode Reader" in device_description:
            barcode_device = device_string
            break

    return barcode_device


# pylint: disable=too-few-public-methods
class BlockingBarcodeReader(object):
    """Blocking Barcode Reader"""

    def __init__(self, device_path):
        self.dev = evdev.InputDevice(device_path)

    def read_barcode(self):
        """Wait for a barcode and return it"""
        out = ""
        for event in self.dev.read_loop():
            if event.type == evdev.ecodes.EV_KEY:
                # Save the event temporarily to introspect it
                data = evdev.categorize(event)
                if data.keystate == 1:  # Down events only
                    key_lookup = SCANCODES.get(data.scancode, "?")
                    if key_lookup == "CRLF":
                        break
                    else:
                        out += key_lookup
        return out

    def close(self):
        """Close the device"""
        self.dev.close()


class ThreadedBarcodeReader(threading.Thread):
    """Threaded Barcode Scanner that holds only the last value"""

    def __init__(self, device_path):
        super(ThreadedBarcodeReader, self).__init__()
        self.dev = evdev.InputDevice(device_path)
        self.daemon = True
        self._barcode_queue = Queue.Queue()

    def run(self):
        """The threaded run method"""
        read_so_far = ""
        for event in self.dev.read_loop():
            if event.type == evdev.ecodes.EV_KEY:
                # Save the event temporarily to introspect it
                data = evdev.categorize(event)
                if data.keystate == 1:  # Down events only
                    key_lookup = SCANCODES.get(data.scancode, "?")
                    if key_lookup == "CRLF":
                        self._barcode_queue.put(read_so_far)
                        read_so_far = ""
                    else:
                        read_so_far += key_lookup

    @property
    def last_barcode_in_queue(self):
        """Last barcode in the queue"""
        last = None
        while True:
            try:
                last = self._barcode_queue.get_nowait()
            except Queue.Empty:
                break
        return last

    @property
    def wait_for_barcode(self):
        """Last barcode property"""
        # We need to timeout every once in a while to allow interrupts to work
        while True:
            try:
                return self._barcode_queue.get(timeout=1)
            except Queue.Empty:
                pass

    @property
    def oldest_barcode_from_queue(self):
        """Get one barcode from the queue if there is one"""
        try:
            return self._barcode_queue.get_nowait()
        except Queue.Empty:
            return None

    def close(self):
        """Close the device"""
        self.dev.close()


SCANCODES = {
    # Scancode: ASCIICode
    0: None,
    1: "ESC",
    2: "1",
    3: "2",
    4: "3",
    5: "4",
    6: "5",
    7: "6",
    8: "7",
    9: "8",
    10: "9",
    11: "0",
    12: "-",
    13: "=",
    14: "BKSP",
    15: "TAB",
    16: "Q",
    17: "W",
    18: "E",
    19: "R",
    20: "T",
    21: "Y",
    22: "U",
    23: "I",
    24: "O",
    25: "P",
    26: "[",
    27: "]",
    28: "CRLF",
    29: "LCTRL",
    30: "A",
    31: "S",
    32: "D",
    33: "F",
    34: "G",
    35: "H",
    36: "J",
    37: "K",
    38: "L",
    39: ";",
    40: '"',
    41: "`",
    42: "LSHFT",
    43: "\\",
    44: "Z",
    45: "X",
    46: "C",
    47: "V",
    48: "B",
    49: "N",
    50: "M",
    51: ",",
    52: ".",
    53: "/",
    54: "RSHFT",
    56: "LALT",
    100: "RALT",
}


if __name__ == "__main__":
    dev_ = detect_barcode_device()
    print(dev_)
    tbs = ThreadedBarcodeReader(dev_)
    tbs.start()
    try:
        while True:
            print("Last barcode: {}".format(tbs.last_barcode_in_queue))
            time.sleep(1)
    except KeyboardInterrupt:
        tbs.close()
