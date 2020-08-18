"""Pressure xgs600 controller"""
from __future__ import print_function
import time
import threading
import queue
from PyExpLabSys.drivers.xgs600 import XGS600Driver as xgs600
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.sockets import LiveSocket


class XGS600Control(threading.Thread):
    """Read all pressures and control states of
        setpoints (ON/OFF/AUTO) in xgs600"""
    def __init__(self, port, socket_name, codenames, user_labels, valve_properties, db_saver=None):
        """
        Args:
            port (int): directory to port of USB to RS232 communication
            socket_name (str): name on net for pushsocket
            codenames (list of str): names for retrieving all pressures and states of valves
            user_labels (list of str): userlabel on each device connected to xgs600
            valve_properties (dict): A dictionarie of valve with a list of properties to
                                     each valve in the form of
                                {valve_name: [channel, device, setpoint_on, setpoint_off], }
                                each valve must have a channel in the XGS600 and a devices
                                to measure the pressure and two setpoints for the pressure
                                for which the valve is on and off
        Returns:
            PushSocket to control XGSvalve states
            PullSocket to acces state of Valves
            PullSocket to acces measured pressure in system
        """
        self.xgs600 = xgs600(port=port)
        time.sleep(0.2)
        threading.Thread.__init__(self)
        #setting the initial setup specific values
        self.codenames = codenames
        self.devices = user_labels
        self.valve_properties = valve_properties
        self.valve_names = list(self.valve_properties.keys())

        #setting the initial program specific values
        self.pressures = None
        self.setpointstates = None
        self.quit = False
        self.update_time = [time.time()]*len(self.valve_names)
        self.updated = [0]*len(self.valve_names)
        names = self.codenames + self.devices
        print(names)

        #starting push-, pull-, and live- sockets
        self.pullsocket = DateDataPullSocket(
            socket_name,
            names,
            timeouts=3.0,
            port=9000,
                )
        self.pullsocket.start()

        self.pushsocket = DataPushSocket(socket_name, action='enqueue')
        self.pushsocket.start()

        self.livesocket = LiveSocket(socket_name, names)
        self.livesocket.start()
        if db_saver is not None:
            self.db_saver = db_saver
            self.db_saver.start()

        self.queue = self.pushsocket.queue

    def value(self):
        """Return two lists
           1. list of floats which is pressures from top down on xgs600 unit
           2. list of string representing the state of each valve connnected"""
        return self.pressures, self.setpointstates

    def update_new_setpoint(self):
        """Update latest values of pressures and setpointstates on pull and live sockets"""
        try:
            for i in range(0, len(self.devices)):
                self.pullsocket.set_point_now(self.devices[i], self.pressures[i])
                self.livesocket.set_point_now(self.devices[i], self.pressures[i])
        except IndexError:
            pass
        self.pullsocket.set_point_now(self.codenames[0], self.pressures)
        self.pullsocket.set_point_now(self.codenames[1], self.setpointstates)

        self.livesocket.set_point_now(self.codenames[0], self.pressures)
        self.livesocket.set_point_now(self.codenames[1], self.setpointstates)
        print('press:', self.pressures)
        print('state:', self.setpointstates)


    def database_saver(self):
        """
        check weather it is time to update database logging.
        This happens at timeout(5min standard) or setpointstate and valve state is incorrect
        """
        for valve in self.valve_names:
            channel = self.valve_properties[valve][0]
            try:
                valve_state = self.setpointstates[channel-1]
                valve_setpoint = self.xgs600.read_setpoint(channel)
            except TimeoutError:
                print('Oops, could not read setpoint of channel, valve_state,\
                        valve_setpoint: ', channel, valve_state, valve_setpoint)

            if valve_setpoint is not 'OFF' and valve_state == False:
                print('Holy Crap it is closed and should be open')
                print('Channel, Valve_state, Valve_setpoint',\
                        channel, valve_state, valve_setpoint)
                if self.updated[channel-1] == 0:
                    print('Saved to Database', channel, valve_state, valve_setpoint)
                    self.db_saver.save_point_now('microreactorng_valve_'+valve, -1)
                    self.updated[channel-1] = 1
                else:
                    print('Not saved to database, due to earlier being saved',\
                            channel, valve_state, valve_setpoint)
                    if time.time() - self.update_time[channel-1] > 300:
                        self.update_time[channel-1] = time.time()
                        self.updated[channel-1] = 0
            else:
                if time.time() - self.update_time[channel-1] > 300:
                    self.db_saver.save_point_now('microreactorng_valve_'+valve, -1)
                    self.update_time[channel-1] = time.time()
                    self.updated[channel-1] = 0
                    print('Saved to Database', channel, valve_state, valve_setpoint)

                self.updated[channel-1] = 0
                print(channel, valve_state, valve_setpoint)

    def run(self):
        while not self.quit:
            while True:
                try:
                    element = self.queue.get(timeout=0.25)
                except queue.Empty:
                    break
                valve = list(element.keys())[0]
                state = element[valve]
                channel = self.valve_properties[valve][0]
                user_label = self.valve_properties[valve][1]
                setpoint_on = self.valve_properties[valve][2]
                setpoint_off = self.valve_properties[valve][3]

                if state.lower() == 'off' or state == 0:
                    self.xgs600.set_setpoint(channel, state)

                else:
                    self.xgs600.set_setpoint_on(
                        channel,
                        sensor_code='user_label',
                        sensor_count=user_label,
                        pressure_on=setpoint_on,
                            )

                    self.xgs600.set_setpoint_off(
                        channel,
                        sensor_code='user_label',
                        sensor_count=user_label,
                        pressure_off=setpoint_off,
                            )
                    
                    self.xgs600.set_setpoint(channel, state)

            #Read values of pressures and states of setpoint
            self.pressures = self.xgs600.read_all_pressures()
            time.sleep(0.1)
            self.setpointstates = self.xgs600.read_setpoint_state()
            time.sleep(0.1)

            self.update_new_setpoint()

            self.database_saver()
