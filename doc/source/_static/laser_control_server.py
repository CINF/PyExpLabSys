# -*- coding: utf-8 -*-

import time
import random
import Queue
from PyExpLabSys.common.sockets import DataPushSocket


class LaserControl(object):
    """Class that controls the giant laser laser on the moon"""

    def __init__(self):
        self.settings = {'power': 100, 'focus': 100, 'target': None}
        self._state = 'idle'
        self._stop = False
        self._temperature_meas = Queue.Queue()
        
        name = 'Laser control, callback socket, for giant laser on the moon'
        self.dps = DataPushSocket(name, action='callback_direct',
                                  callback=self.callback,
                                  return_format='json')
        self.dps.start()

    def callback(self, data):
        """Callback and central control function"""
        method_name = data.pop('method')  # Don't pass the method name on
        method = self.__getattribute__(method_name)
        return method(**data)

    def update_settings(self, **kwargs):
        """Update settings"""
        for key in kwargs.keys():
            if key not in self.settings.keys():
                message = 'Not settings for key: {}'.format(key)
                raise ValueError(message)
        self.settings.update(kwargs)
        print 'Updated settings with: {}'.format(kwargs)
        return 'Updated settings with: {}'.format(kwargs)

    def state(self, state):
        """Set state"""
        self._state = state
        print 'State set to: {}'.format(state)
        return 'State set to: {}'.format(state)

    def run(self):
        """Monitor state and run temperature monitorint"""
        print 'Run started'
        while not self._stop:
            if self._state == 'active':
                self.monitor_temperature()
            time.sleep(1)
        self.dps.stop()
        print 'Run ended'

    def stop(self):
        """Stop the laser controller"""
        self._state = 'idle'
        self._stop = True
        print 'Stopped'
        return 'Stopped'

    def monitor_temperature(self):
        """Monitor the temperature"""
        while self._state == 'active':
            item = [time.strftime('%Y-%m-%d %X'), random.randint(30, 300)]
            self._temperature_meas.put(item)
            print 'At {} temperature is {}'.format(*item)
            time.sleep(1)

    def get_temperature(self):
        """Get the temperature measurements available"""
        out= []
        for _ in range(self._temperature_meas.qsize()):
            out.append(self._temperature_meas.get())
        return out


if __name__ == '__main__':
    laser_control = LaserControl()
    laser_control.run()