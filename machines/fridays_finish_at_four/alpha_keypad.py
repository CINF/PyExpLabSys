
"""Example implementation of the old telephone alphanumeric keyboard"""


from time import sleep, time
from queue import Empty
from PyExpLabSys.drivers.deltaco_TB_298 import (
    detect_keypad_device, ThreadedKeypad, KEYS_TO_CHARS,
)

LAYOUT = {
    '1': '1',
    '2': 'abc2',
    '3': 'def3',
    '4': 'ghi4',
    '5': 'jkl5',
    '6': 'mno6',
    '7': 'pqrs7',
    '8': 'tuv8',
    '9': 'wxyz9',
    '0': '0',
}


# Note, the main function here is way too long, and should be refactored somehow


def main():
    """Continously read """
    devicepath = detect_keypad_device()
    print(devicepath)
    device = ThreadedKeypad(devicepath)
    device.start()

    repeat_time = 0.3
    alpha = False
    prompt = 'Alpha "{: <5}". / to toggle: {: <40}'
    gathered = ''
    last_number = ''
    last_number_time = 0
    # The edited variable keeps tracks of whether the output string has been edited below
    edited = True
    
    while True:
        print('\r' * 80, prompt.format(alpha, gathered), end='', sep='')
        # The timeout on the queue only necessary, because we want to allow
        # for a keyboard interrupt
        try:
            key = device.key_pressed_queue.get(timeout=0.01)
        except Empty:
            continue
        except KeyboardInterrupt:
            device.stop()
            break

        # Special keys
        if key == 'KEY_BACKSPACE':
            gathered = gathered[: -1]
            continue
        # On enter, we break out of the infinite while loop and are done
        elif key == 'KEY_KPENTER':
            break
        # / changes between normal keyboard and alphanumeric
        elif key == 'KEY_KPSLASH':
            alpha = not alpha
            continue            

        # Get the number
        try:
            number = KEYS_TO_CHARS[key]
        except KeyError:
            continue

        if not number in '0123456789':
            continue

        edited = False
        now = time()
        diff = now - last_number_time
        # If we are not in alpha numeric state, add the char
        if not alpha:
            gathered += number
            edited = True
        # elif we are in alpha mode, the repeat time has passed of the input
        # is empty, add the char
        elif diff > repeat_time or gathered == '':  # Alpha code
            gathered += LAYOUT[number][0]
            edited = True
        # elif we are in alpha mode and the repeat time hasn't passed, change
        # to next char in cycle
        elif diff < repeat_time:
            last_char = gathered[-1]
            # Figure out what the last number key pressed was
            for last_number, chars in LAYOUT.items():
                if last_char in chars:
                    break
            else:
                # This really shouldn't happen
                raise RuntimeError

            # If the numbers pressed within repeat time are the same
            if number == last_number:
                # Replace the char with the next one in the cycle
                position = chars.index(last_char)
                new_position = (position + 1) % len(chars)
                new_char = chars[new_position]
                gathered = gathered[: -1] + new_char
                edited = True
            else:
                gathered += LAYOUT[number][0]
                edited = True

        if edited:
            last_number = number
            last_number_time = now


    device.stop()
    print("\n\nEntered:", gathered)
    

main()
