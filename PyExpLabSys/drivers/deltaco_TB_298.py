
"""Driver with line reader for the Deltaco TB-298 Keypad"""

import glob
import evdev
import select
from time import sleep, time
from threading import Thread
from queue import Queue, Empty

from PyExpLabSys.common.supported_versions import python3_only
python3_only(__file__)


KEYS_TO_CHARS = {'KEY_KP{}'.format(n): str(n) for n in range(10)}
KEYS_TO_CHARS.update({
    'KEY_KPSLASH': '/',
    'KEY_KPASTERISK': '*',
    'KEY_KPMINUS': '-',
    'KEY_KPPLUS': '+',
    'KEY_KPDOT': '.',
})



def detect_keypad_device():
    """Return the input device path of the Deltaco TB-298 Keypad

    Iterates over all devices in /dev/input/event?? and looks for one that has
    the Deltaco Keypad vendor and product id and has a "1" key

    Returns:
        str: The Keypad device path
    """
    barcode_device = None
    for device_string in glob.glob('/dev/input/event*'):
        try:
            tmp_dev = evdev.InputDevice(device_string)
        except OSError:
            continue
        else:
            device_information = tmp_dev.info
            # Check for vendor and product ids
            if not (device_information.vendor == 0x04d9 and device_information.product == 0x1203):
                continue

            available_keys = tmp_dev.capabilities(verbose=True)[('EV_KEY', 1)]
            tmp_dev.close()
            if ('KEY_1', 2) in available_keys:
                return device_string


STOP = object()


class ThreadedKeypad(Thread):
    """Threaded keypad reader

    Attributes:
        line_queue (queue.Queue): Queue of enter separated lines entered
        event_queue (queue.Queue): Queue of key pad events
        key_pressed (queue.Queue): Queue of pressed keys (only one entry will be added if
            the key is held down)
        device (evdev.InputDevice): The input device
    """

    def __init__(self, device_path, line_chars='0123456789', max_queue_sizes=None):
        """Instantiate local variables

        Holds 3 queues

        Args:
            device_path (str): Path of the inpu device to use e.g: '/dev/input/event0'
            line_chars (str): String of accepted characters in a line. Default value is
                '0123456789'
            max_queue_sizes: Dict used to overwrite the default max queue size of 1000
                elements. The keys are 'line', 'event' and 'key_pressed' and the values
                are ints.
        """
        super().__init__()
        self._continue_reading = True
        self.device = evdev.InputDevice(device_path)
        self._gathered_line = ''
        self.line_chars = line_chars

        # Create queues
        _max_queue_sizes = {'line': 1024, 'event': 1024, 'key_pressed': 1024}
        if max_queue_sizes:
            _max_queue_sizes.update(max_queue_sizes)
        self.line_queue = Queue(maxsize=_max_queue_sizes['line'])
        self.event_queue = Queue(maxsize=_max_queue_sizes['event'])
        self.key_pressed_queue = Queue(maxsize=_max_queue_sizes['key_pressed'])

    def run(self):
        """Main run method"""
        while self._continue_reading:
            # Check if there is anything to read on the device
            read_list, _, _ = select.select([self.device.fd], [], [], 0.1)
            if read_list:
                for event in self.device.read():
                    if event.type == evdev.ecodes.EV_KEY:
                        self.handle_event(event)

    def handle_event(self, event):
        """Handle an event"""
        categorized_event = evdev.categorize(event)
        self.event_queue.put(categorized_event)

        if categorized_event.keystate == 0:  # Key up
            # Insert into key_pressed_queue
            key_code = categorized_event.keycode
            self.key_pressed_queue.put(key_code)

            # Insert chars in line
            if key_code in KEYS_TO_CHARS:
                char = KEYS_TO_CHARS[key_code]
                if char in self.line_chars:
                    self._gathered_line += char
            elif key_code == 'KEY_BACKSPACE':
                self._gathered_line = self._gathered_line[:-1]
            elif key_code == 'KEY_KPENTER':
                self.line_queue.put(self._gathered_line)
                self._gathered_line = ''

    def stop(self):
        """Stop the thread and put deltaco_TP_298.STOP in queues"""
        self._continue_reading = False
        while self.is_alive():
            sleep(0.1)
        self.device.close()
        self.line_queue.put(STOP)
        self.event_queue.put(STOP)
        self.key_pressed_queue.put(STOP)


def module_demo():
    """Simple module demo"""
    # Get reader
    device_path = detect_keypad_device()
    reader = ThreadedKeypad(device_path)
    reader.start()
    try:
        while True:
            # Get pending lines
            while True:
                try:
                    line = reader.line_queue.get(timeout=0)
                    print("LINE", line)
                except Empty:
                    break

            # Get pending events
            while True:
                try:
                    event = reader.event_queue.get(timeout=0)
                    print("EVENT", event)
                except Empty:
                    break

            # Get pending key presses
            while True:
                try:
                    key_pressed = reader.key_pressed_queue.get(timeout=0)
                    print("KEY PRESSED", key_pressed)
                except Empty:
                    break
            sleep(0.1)
    except KeyboardInterrupt:
        reader.stop()


if __name__ == '__main__':
    module_demo()
