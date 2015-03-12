"""This module contains general purpose decorators"""

import functools


def execute_on_exception(name_of_shutdown_method):
    """Decorates a method to execute a named method if an exception is raised

    Args:
        name_of_shutdown_method (str): The name of the method (on the same
            object as the decorated method) to call if the decorated methods
            raises an exception
    """
    def decorator(method):
        """The decorator for the method"""
        @functools.wraps(method)
        def new_method(*args, **kwargs):
            """Decorated method"""

            # args[0] is the object (self)
            shutdown_method = getattr(args[0], name_of_shutdown_method)

            try:
                out = method(*args, **kwargs)
            except:
                shutdown_method()
                # Re-raise for good measure
                raise
            return out
        return new_method
    return decorator
