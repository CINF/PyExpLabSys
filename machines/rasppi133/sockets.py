# -*- coding: utf-8 -*-
from PyExpLabSys.common.sockets import DataPushSocket, DateDataPullSocket
import time

class MFC_control(object):

    def __init__(self):
        self.settings = {'sp1': 0., 'sp2': 0., 'sp3': 0., 'sp4': 0., 'sp5': 5., 'spP':1.}
        self.power_MFC('ON')
        
        self.name = 'Sigrun_massflow_pressure_setpoint_reciever'
        self.socket = DataPushSocket(self.name, action='callback_direct', port=8501, callback=self.callback, return_format='json')

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

    def reset_arduino(self):
        pass

    def power_MFC(self, state):
        if state not in ['ON', 'OFF']:
            print(state+' was not recognized as a possible setting')
        else:
            self.MFC_state = state
            if self.MFC_state == 'ON':
                pass
            elif self.MFC_state == 'OFF':
                pass
            print('State of MFC power was set to '+state)
            return 'State of MFC power was set to '+state
        
    def stop(self):
        self.socket.stop()
        print('Control socket stopped')
        return 'Control socket stopped'

class data_socket(object):

    def __init__(self):
        self.name = 'Sigrun_Massflow_control'
        self.data_entries = ['MFC1','MFC2','MFC3','MFC4','MFC5','SP1','SP2','SP3','SP4','SP5','P','SPP']
        self.port = 9001
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
    MFC = MFC_control()
    data_sock = data_socket()
    try:
        while True:
            data_sock.set_point_now('SP1', MFC.settings['sp1'])
            data_sock.set_point_now('SP2', MFC.settings['sp2'])
            data_sock.set_point_now('SP3', MFC.settings['sp3'])
            data_sock.set_point_now('SP4', MFC.settings['sp4'])
            data_sock.set_point_now('SP5', MFC.settings['sp5'])
            data_sock.set_point_now('SPP', MFC.settings['SPP'])            
    except KeyboardInterrupt:
        data_sock.stop()
        MFC.stop()
