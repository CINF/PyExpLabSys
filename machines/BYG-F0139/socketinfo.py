# -*- coding: utf-8 -*-
"""
Created on Wed Aug 19 17:13:17 2015

@author: pi
"""

INFO = {}
INFO['tabs_temperatures'] = {'host': 'localhost',
                             'port': 9000, 
                             'codenames':['tabs_guard_temperature_inlet',
                                          'tabs_floor_temperature_inlet',
                                          'tabs_ceiling_temperature_inlet',
                                          'tabs_cooling_temperature_inlet', 
                                          'tabs_guard_temperature_outlet',
                                          'tabs_floor_temperature_outlet',
                                          'tabs_ceiling_temperature_outlet',
                                          'tabs_cooling_temperature_outlet', ]}

INFO['tabs_setpoints'] = {'host': 'localhost',
                          'port': 9001,
                          'codenames':['tabs_guard_temperature_setpoint',
                                          'tabs_floor_temperature_setpoint',
                                          'tabs_ceiling_temperature_setpoint',
                                          'tabs_cooling_temperature_setpoint', ]}
INFO['tabs_pids'] = {'host': 'localhost',
                     'port': 9002,
                     'codenames':['tabs_guard_pid_value',
                                          'tabs_floor_pid_value',
                                          'tabs_ceiling_pid_value',
                                          'tabs_cooling_pid_value', ]}
INFO['tabs_valve'] = {'host': 'localhost',
                      'port': 9003,
                      'codenames':['tabs_guard_valve_heating',
                                          'tabs_floor_valve_heating',
                                          'tabs_ceiling_valve_heating',
                                          'tabs_cooling_valve_heating', 
                                          'tabs_guard_valve_cooling',
                                          'tabs_floor_valve_cooling',
                                          'tabs_ceiling_valve_cooling',
                                          'tabs_cooling_valve_cooling']}
INFO['tabs_multiplexer'] = {'host': 'localhost',
                      'port': 9005,
                      'codenames':['tabs_guard_temperature_delta',
                                          'tabs_floor_temperature_delta',
                                          'tabs_ceiling_temperature_delta',
                                          'tabs_cooling_temperature_delta', 
                                          'tabs_room_temperature_110',]}

INFO['tabs_all'] = {'host': 'localhost',
                      'port': 9006,
                      'codenames':['tabs_guard_temperature_inlet',
                                          'tabs_floor_temperature_inlet',
                                          'tabs_ceiling_temperature_inlet',
                                          'tabs_cooling_temperature_inlet', 
                                          'tabs_guard_temperature_outlet',
                                          'tabs_floor_temperature_outlet',
                                          'tabs_ceiling_temperature_outlet',
                                          'tabs_cooling_temperature_outlet', 
                                          'tabs_guard_temperature_setpoint',
                                          'tabs_floor_temperature_setpoint',
                                          'tabs_ceiling_temperature_setpoint',
                                          'tabs_cooling_temperature_setpoint', 
                                          'tabs_guard_pid_value',
                                          'tabs_floor_pid_value',
                                          'tabs_ceiling_pid_value',
                                          'tabs_cooling_pid_value', 
                                          'tabs_guard_valve_heating',
                                          'tabs_floor_valve_heating',
                                          'tabs_ceiling_valve_heating',
                                          'tabs_cooling_valve_heating', 
                                          'tabs_guard_valve_cooling',
                                          'tabs_floor_valve_cooling',
                                          'tabs_ceiling_valve_cooling',
                                          'tabs_cooling_valve_cooling']}
"""INFO['tabs_heaters'] = {
                        'host': 'localhost',
                        'port': 9004,
                        'codenames':['tabs_guard_heater',
                                     'tabs_floor_heater',
                                     'tabs_ceiling_heater'
                                   ]
                        }
"""
1+1
"""                   
for sy in ['tabs_guard', 'tabs_floor', 'tabs_ceiling', 'tabs_cooling', 'tabs_ice']:
    self.SYSTEMS[sy] = {'temperature_inlet': None, # float in C
                        'temperature_outlet': None, # float in C
                        'temperature_setpoint': None, # float in C
                        'valve_cooling': None, # float 0-1
                        'valve_heating': None, # float 0-1
                        'pid_value': None, # float -1-1
                        'water_flow': None} # float in l/min  
"""
### Settings ###
# RTD
# gaurd 4w 1000Ohm
# floor 4w 1000Ohm


if __name__ == '__main__':
    import sys
    sys.path.insert(1, '/home/pi/PyExpLabSys')
    from PyExpLabSys.common.sockets import DateDataPullSocket
    import time
    #PullSocket = {}
    #for key, value in INFO.items():
    #    PullSocket[key] = DateDataPullSocket(key, value['codenames'], timeouts=[60.0]*len(value['codenames']), port = value['port'])
    #    PullSocket[key].start()
    #time.sleep(10)
    #for key, value in INFO.items():
    #    PullSocket[key].stop()