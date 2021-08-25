# -*- coding: utf-8 -*-
from drivers import Heater
import time
from sockets import furnace_control, data_socket

"""
#Initiation
"""
#push socket
furnace = furnace_control() #on port 8501
heater = Heater()

#Pull socket
data_sock = data_socket()

"""
#setpoint in
"""
print('Furnace started on '+time.ctime()+' with PID parameters ('+str(heater.pid.pid_p)+','+str(heater.pid.pid_i)+')')
print('\n\n')
start_time = time.time()
loop_time = time.time()-start_time
update_time = 0.44
try:
    while True:
        try:
        #if True:
            if  (update_time-loop_time) >= 0:
                #if less than a second has passed, since last loop, wait until a second has passed
                time.sleep(update_time-loop_time)
            print('T: ( '+str(heater.temperature())+' / '+str(heater.setpoint())+' ), V/I: ( '+str(heater.voltage())+' / '+str(heater.current())+' ), error P/I: ('+str(round(heater.pid.error,2))+' / '+str(round(heater.pid.int_err,2))+' )    ')
            heater.update_setpoint(furnace.settings['sp'])
            heater.heat()
            rel_time = time.time()-start_time
            data_sock.set_point_now('temperature', [rel_time, heater.temperature()])
            data_sock.set_point_now('setpoint', [rel_time, heater.setpoint()])
            data_sock.set_point_now('voltage', [rel_time, heater.voltage()])
            data_sock.set_point_now('current', [rel_time, heater.current()])
            data_sock.set_point_now('p error', [rel_time, heater.pid.error])
            data_sock.set_point_now('int error', [rel_time, heater.pid.int_err])
            loop_time = time.time()-start_time-loop_time
        except:
            time.sleep(0.1)
            continue
except KeyboardInterrupt:
    print('Script interrupted. Heating stopped on '+time.ctime())
    heater.update_setpoint(-9999)
    furnace.stop()
    data_sock.stop()
    print('Quitting')
