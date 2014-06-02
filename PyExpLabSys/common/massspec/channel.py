# pylint: disable=R0913,W0142

"""This module contains the implementation of a general purpose mass
spectrometer channel
"""


class MSChannel(object):
    """ A mass spec channel """

    required_fields = ['mass']
    optional_fields = ['channel_range', 'time', 'delay', 'label', 'color',
                       'active', 'auto_label']

    def __init__(self, mass, channel_range='1E-7', time=100, delay=100,
                 label='', color='#000000', active=True, auto_label=True):
        """Initialize the channel

        Arguments:
        mass    the mass to track (float or int)

        Keyword arguments:
        channel_range   the range as a str, one of '1E-5', '1E-7', '1E-9' and
                        '1E-11'
        time        time in milliseconds (int) to measure
        delay       time in milliseconds (int) to wait before proceeding
        label       the label for this channel
        color       the color of the graph for this channel as a hex string
                    e.g. '#ABCDEF'
        active      whether the channel is active (bool)
        auto_label  whether to update the label automatically (bool)
        """
        self._range_translation = {'1E-5': 'L', '1E-7': 'M', '1E-9': 'H',
                                   '1E-11': 'VH'}
        # Internally store the channel properties in a dict
        self._channel_desc = \
            {'mass': mass, 'channel_range': channel_range, 'time': time,
             'delay': delay, 'label': label, 'color': color, 'active': active,
             'auto_label': auto_label}
        self._update_label()

    def __str__(self):
        """Return a str representation"""
        active_str = 'Active' if self.active else 'In-active'
        out = '{active_str} channel for mass {mass}, range: {channel_range}, '\
              'time: {time} and delay: {delay}\n'\
              '+label: {label}\n'\
              '+color: {color}, active: {active}, auto_label: {auto_label}'\
            .format(active_str=active_str, **self._channel_desc)
        return out

    @property
    def to_dict(self):
        """Return a dict representation of the channel"""
        return self._channel_desc

    @classmethod
    def from_dict(cls, channel_dict):
        """Initialize a channel from a dict. The dict must contain the key
        mass and may contain the keys 'range_', 'time', 'delay', 'color',
        'active' and 'auto_label' as specified in the __init__ method
        """
        for key in cls.required_fields:
            if not key in channel_dict:
                message = 'The key \'{}\' is missing'.format(key)
                raise ValueError(message)
        for key in channel_dict:
            if not key in cls.required_fields + cls.optional_fields:
                message = 'The key \'{}\' is not allowed'.format(key)
                raise ValueError(message)
        mass = channel_dict.pop('mass')
        return cls(mass, **channel_dict)

    @property
    def mass(self):
        """The mass property"""
        return self._channel_desc['mass']

    @mass.setter
    def mass(self, mass):  # pylint: disable=C0111
        self._channel_desc['mass'] = mass
        self._update_label()

    @property
    def channel_range(self):
        """The channel_range property"""
        return self._channel_desc['channel_range']

    @channel_range.setter
    def channel_range(self, channel_range):  # pylint: disable=C0111
        if channel_range in self._range_translation:
            self._channel_desc['channel_range'] = channel_range
            self._update_label()
        else:
            message = '\'{}\' is not a valid value for channel_range, see '\
                      'docstring for __init__'.format(channel_range)
            raise ValueError(message)

    @property
    def time(self):
        """The time property"""
        return self._channel_desc['time']

    @time.setter
    def time(self, time):  # pylint: disable=C0111
        self._channel_desc['time'] = time

    @property
    def delay(self):
        """The delay property"""
        return self._channel_desc['delay']

    @delay.setter
    def delay(self, delay):  # pylint: disable=C0111
        self._channel_desc['delay'] = delay

    @property
    def label(self):
        """The label property"""
        return self._channel_desc['label']

    @label.setter
    def label(self, label):  # pylint: disable=C0111
        if self.auto_label:
            message = 'Cannot set label when auto_label is True'
            raise AttributeError(message)
        else:
            self._channel_desc['label'] = label

    @property
    def color(self):
        """The color property"""
        return self._channel_desc['color']

    @color.setter
    def color(self, color):  # pylint: disable=C0111
        self._channel_desc['color'] = color

    @property
    def active(self):
        """The active property"""
        return self._channel_desc['active']

    @active.setter
    def active(self, active):  # pylint: disable=C0111
        self._channel_desc['active'] = active

    @property
    def auto_label(self):
        """The auto_label property"""
        return self._channel_desc['auto_label']

    @auto_label.setter
    def auto_label(self, auto_label):  # pylint: disable=C0111
        self._channel_desc['auto_label'] = auto_label

    def _update_label(self):
        """Update the label if auto_label is active"""
        if self.auto_label:
            mass = self.mass
            if abs(int(mass) - mass) < 1E-3:
                mass = int(mass)
            self._channel_desc['label'] = 'M{}{}'.\
                format(mass, self._range_translation[self.channel_range])
            return self.label
