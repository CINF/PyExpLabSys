"""This module contains general purpose functions"""

import time
import datetime


def loop_class_on_exceptions(
    class_to_loop, tuple_of_exceptions_to_ignore=None, wait_between_loops=600, **kwargs
):
    """Reinitialize and run a class on certain errors by wrapping in a try-except clause

    Args:
        class_to_loop (class): The main class you want to restart (loop) on errors
        tuple_of_exceptions_to_ignore (tuple or None): A tuple of exceptions to trigger
            the "stop" method of the main class followed by reinitializing the main
            class and calling its "run" method
        wait_between_loops (float or int): Time in seconds to wait after stopping the
            main class before restarting it

        **kwargs: Any additional keyword arguments are passed to the main class __init__

    Usage:
        from PyExpLabSys.common.functions import loop_class_on_exceptions

        class MyClass:
            def __init__(self, my_message='Default'):
                self.msg = my_message

            def run(self):
                print(self.msg)
                raise IOError('An IOError is raised and handled by restarting class')

            def stop(self):
                # Does nothing in this case, but must be present
                pass

        # Main loop:
        errors = (IOError, ValueError)
        loop_class_on_exceptions(
            MyClass,
            tuple_of_exceptions_to_ignore=errors,
            wait_between_loops=5,
            my_message='Hello world!',
            )

    """

    # Check arguments
    msg = ''
    if not isinstance(class_to_loop, type):
        msg = (
            'First argument must be the instance of the class you want looped on',
            ' errors. This class must also have a "run" method.',
        )
    if not tuple_of_exceptions_to_ignore is None:
        if not isinstance(tuple_of_exceptions_to_ignore, tuple):
            msg = (
                'Second argument must be ´None´ or a tuple of exceptions, which should',
                ' trigger a restart of the class.',
            )
        else:
            if KeyboardInterrupt in tuple_of_exceptions_to_ignore:
                msg = (
                    'KeyboardInterrupt is reserved for breaking out of the outer loop!'
                )
    if msg:
        raise TypeError(msg)

    # Start main loop
    if tuple_of_exceptions_to_ignore is None:
        print('Starting main class without cathing any errors (no looping)')
        main_class = class_to_loop(**kwargs)
        main_class.run()
        SystemExit()

    while True:
        try:
            now = datetime.datetime.now()
            now = now.strftime('%Y-%m-%D %H:%M:%S')
            print(
                '{}:\n'.format(now),
                'Starting main class while catching following errors: ',
                '{}.\n'.format(tuple_of_exceptions_to_ignore),
                'Use KeyboardInterrupt to break out of this loop.\n',
                '_' * 10,
            )
            main_class = class_to_loop(**kwargs)
            main_class.run()
        except KeyboardInterrupt:
            print('Stopping script...')
            main_class.stop()
            break
        except tuple_of_exceptions_to_ignore as error:
            now = datetime.datetime.now()
            now = now.strftime('%Y-%m-%D %H:%M:%S')
            print('\n{}\nCaught error: {}'.format(now, error))
            print('Stopping script. Restarting in {} s:'.format(wait_between_loops))
            main_class.stop()
            t0 = time.time()
            t = t0
            while t - t0 < wait_between_loops:
                time.sleep(1)
                t = time.time()
                print('{:>5.1f} s   '.format(wait_between_loops - (t - t0)), end='\r')
            print('_' * 10)
            continue
