# -*- coding: utf-8 -*-
from PyExpLabSys.drivers.dataq_comm import DataQ
from drivers import i2c_communicate, pressure_control, Relay, loading_animation, MFC_setpoint_1volt_shift, MFC_data_1volt_shift, arduino
import time
from sockets import MFC_control, data_socket

"""
#Initiation
"""
relay = Relay()
i2c_connection_lost = False
shut_down_procedure = False
arduino_control = arduino()

relay.MFC_powersupply_ON()
print('power up mass flow controllers')

print('\n')
loading_animation(9) #they take some time to start

#dataq = DataQ('/dev/ttyACM0')
#dataq.add_channel(1)
#dataq.start_measurement()

#push socket
MFC_sock = MFC_control() #on port 8501

#Pull socket
data_sock = data_socket()

"""
#setpoint in
"""
print('Gas flow started on '+time.ctime())
print('\n\n')
start_time = time.time()
loop_time = time.time()-start_time
update_time = 0.44
try:
    while True:
        if  (update_time-loop_time) > 0:
             #if less than a second has passed, since last loop, wait until a second has passed
            time.sleep(update_time-loop_time)
        for setpoint in ['sp1','sp2','sp3','sp4','sp5']:
            if MFC_sock.settings[setpoint] < 0:
                MFC_sock.settings[setpoint] = 0.
            elif MFC_sock.settings[setpoint] > 100:
                MFC_sock.settings[setpoint] = 100.
        sp1, sp2, sp3, sp4, sp5 = MFC_sock.settings['sp1'], MFC_sock.settings['sp2'], MFC_sock.settings['sp3'], MFC_sock.settings['sp4'], MFC_sock.settings['sp5'] 
        _flow_ = i2c_communicate(0x14, round(sp1*2.55), round(sp2*2.55), round(sp3*2.55), round(sp4*2.55), round(sp5*2.55))
        if MFC_sock.settings['spP'] < 0:
            MFC_sock.settings['spP'] = 0
        elif MFC_sock.settings['spP'] > 10.1: #here is the pressure limit
            MFC_sock.settings['spP'] = 10.1
        spP = MFC_sock.settings['spP']
        _pressure_ = pressure_control(spP)
        if _flow_[4] == -1000 or _pressure_ < -1:
            time.sleep(0.5)
            _flow_ = i2c_communicate(0x14, round(sp1*2.55), round(sp2*2.55), round(sp3*2.55), round(sp4*2.55), round(sp5*2.55))
            _pressure_ = pressure_control(spP)
            if _flow_[4] == -1000 or _pressure_ < -1:
                print('\n')
                print('connection to arduino seems lost on '+time.ctime())
                while True:
                    print('Entered reset-mode.')
                    arduino_control.reset_arduino()
                    arduino_control.reset_pres_arduino()
                    time.sleep(0.5)
                    _flow_ = i2c_communicate(0x14, round(sp1*2.55), round(sp2*2.55), round(sp3*2.55), round(sp4*2.55), round(sp5*2.55))
                    _pressure_ = pressure_control(spP)
                    if _flow_[4] != -1000 and _pressure_ > 0:
                        print('Reset succesfull, at '+time.ctime())
                        break
            _flow_ = i2c_communicate(0x14, round(sp1*2.55), round(sp2*2.55), round(sp3*2.55), round(sp4*2.55), round(sp5*2.55))
            _pressure_ = pressure_control(spP)
        if shut_down_procedure:
            _pressure_ = pressure_control(0.2)
            time.sleep(5)
            relay.MFC_powersupply_OFF()
            MFC_sock.stop()
            data_sock.stop()
            break 
            
        print('('+str(round(sp1,1))+'[%]/'+str(round(_flow_[0]/10.23,1))+')('+str(round(sp2,1))+'[%]/'+str(round(_flow_[1]/10.23,1))+')('+str(round(sp3,1))+'[%]/'+str(round(_flow_[2]/10.23,1))+')('+str(round(sp4,1))+'[%]/'+str(round(_flow_[3]/10.23,1))+')('+str(round(sp5,1))+'[%]/'+str(round(_flow_[4]/10.23,1))+')(',str(round(spP,1))+'[bar]/'+str(round(_pressure_,1))+')       ',end = '\r')
        data_sock.set_point_now('MFC1', _flow_[0]/10.23)
        data_sock.set_point_now('SP1', sp1)
        data_sock.set_point_now('MFC2', _flow_[1]/10.23)
        data_sock.set_point_now('SP2', sp2)
        data_sock.set_point_now('MFC3', _flow_[2]/10.23)
        data_sock.set_point_now('SP3', sp3)
        data_sock.set_point_now('MFC4', _flow_[3]/10.23)
        data_sock.set_point_now('SP4', sp4)
        data_sock.set_point_now('MFC5', _flow_[4]/10.23)
        data_sock.set_point_now('SP5', sp5)
        data_sock.set_point_now('P', _pressure_)
        data_sock.set_point_now('SPP', spP)
        loop_time = time.time()-start_time-loop_time
except KeyboardInterrupt:
    print('Script interrupted. Flow stopped on '+time.ctime())
    _pressure_ = pressure_control(0.2)
    _flow_ = i2c_communicate(0x14, 0, 0, 0, 0, 0)
    #dataq.stop_measurement()
    MFC_sock.stop()
    data_sock.stop()
    print('power down mass flow controllers')
    loading_animation(5)
    relay.MFC_powersupply_OFF()
    print('Quitting')
