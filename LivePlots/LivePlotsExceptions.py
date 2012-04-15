
""" Custom exceptions """


class LivePlotsErrors(Exception):
    """ Base class for all exceptions in this module """

    def __str__(self):
        return self.msg


class NLinesError(LivePlotsErrors):
    """ Exception raised when input fails to have one item per line

    Attributes:
        msg -- explanantion of the error
    """

    def __init__(self, n_input, n_lines):
        Exception.__init__(self)
        self.msg = ('The length of your input {0} does not match the number '
                    'of lines {1}').format(n_input, n_lines)


class NDataError(LivePlotsErrors):
    """ Exception raised when input fails to have the same legth and the number
    of points

    Attributes:
        msg -- explanantion of the error
    """

    def __init__(self, n_input, n_points):
        self.msg = ('The length of your input {0} does not match the number '
                    'of points {1}').format(n_input, n_points)
