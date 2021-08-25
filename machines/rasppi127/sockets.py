# -*- coding: utf-8 -*-
from PyExpLabSys.common.sockets import DataPushSocket, DateDataPullSocket
import time

class furnace_control(object):

    def __init__(self):
        self.settings = {'sp': -9999, 'hr': None}
                
        self.name = 'Sigrun_furnace'
        self.socket = DataPushSocket(self.name, action='callback_direct', port=8503, callback=self.callback, return_format='json')

        self.socket.start()

    def callback(self, data):
        method_name = data.pop('method')
        method = self.__getattribute__(method_name)
        return method(**data)

    def update_settings(self, **kwargs):
        for key in kwargs.keys():
            if key not in self.settings.keys():
                raise ValueError(key+' was not recognized as a possible setting')
        self.settings.update(kwargs)
        print('Update settings with: {}'.format(kwargs))
        return 'Updated settings with: {}'.format(kwargs)

    def stop(self):
        self.socket.stop()
        print('Control socket stopped')
        return 'Control socket stopped'

class data_socket(object):

    def __init__(self):
        self.name = 'Sigrun_furnace_temperature'
        self.data_entries = ['temperature','setpoint','voltage','current','p error','int error']
        self.port = 9003
        self.socket = DateDataPullSocket(self.name, self.data_entries, port=self.port)
        self.socket.start()
    
    def set_point_now(self, entry, data_point):
        if entry not in self.data_entries:
            raise KeyError('Key not found in data entries')
            return
        self.socket.set_point_now(entry, data_point)
    
    def stop(self):
        self.socket.stop()
        print('Data socket stopped')
        return 'Data socket stopped'

class pirani_socket(object):
    def __init__(self):
        self.name = 'Sigrun_GC_smart_pirani'
        self.data_entries = ['pressure', 'temperature']
        self.port = 9004
        self.socket = DateDataPullSocket(self.name, self.data_entries, port=self.port)
        self.socket.start()
    
    def set_point_now(self, entry, data_point):
        if entry not in self.data_entries:
            raise KeyError('Key not found in data entries')
            return
        self.socket.set_point_now(entry, data_point)
    
    def stop(self):
        self.socket.stop()
        print('Data socket stopped')
        return 'Data socket stopped'

if __name__ == '__main__':
    furnace = furnace_control()
    data_sock = data_socket()
    try:
        while True:
            data_sock.set_point_now('sp', furnace.settings['sp1'])
            data_sock.set_point_now('hr', hr.settings['sp1'])
    except KeyboardInterrupt:
        data_sock.stop()
        MFC.stop()
