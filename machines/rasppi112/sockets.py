# -*- coding: utf-8 -*-
from PyExpLabSys.common.sockets import DateDataPullSocket, DataPushSocket
import time
from drivers import Relay

class GC_start_stop_socket(object):

    def __init__(self):
        self.state = 'alive'
        self.injection_number = 0
        self.relay = Relay()
        
        self.name = 'Sigrun_GC_start_stop'
        self.socket = DataPushSocket(self.name,
                                     action='callback_direct',
                                     callback=self.callback,
                                     return_format='json',
                                     port=8502)
        self.socket.start()

    def callback(self, data):
        method_name = data.pop('method')
        method = self.__getattribute__(method_name)
        return method(**data)

    def stop(self):
        self.socket.stop()

    def start_run(self):
        self.relay.start_GC()
        print('Starting GC on '+time.ctime())
        self.run_in_progress = True
    
    def stop_run(self):
        self.relay.stop_GC()
        print('Stopping GC on '+time.ctime())
        self.run_in_progress = False

class pressure_socket(object):
    
    def __init__(self):
        self.name = 'Sigrun_pressure'
        self.data_entries = ['pressure']
        self.port = 9009
        self.socket = DateDataPullSocket(self.name, self.data_entries, port=self.port)
        self.socket.start()
    
    def stop(self):
        self.socket.stop()

    def set_point_now(self, data_point):
        self.socket.set_point('pressure',data_point)
        
class GC_data_socket(object):

    def __init__(self):
        self.name = 'Sigrun_Gas_Chromatograph'
        self.data_entries = ['ready_voltage','retention_time','FID low V','FID high V','TCD low V','TCD high V']
        self.port = 9002
        self.socket = DateDataPullSocket(self.name, self.data_entries, port=self.port)
        self.socket.start()

    def stop(self):
        self.socket.stop()

    def set_point_now(self, entry, data_point):
        if entry not in self.data_entries:
            raise KeyError('Key not found in data_entries')
            return
        self.socket.set_point(entry, data_point)
        
