"""Run a heat ramp for the Omicron TPD stage """
import logging
import time
import socket
#import threading
import pid as PID
from PyExpLabSys.common.socket_clients import DateDataPullClient
from PyExpLabSys.common.supported_versions import python2_and_3
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
#python2_and_3(__file__)

#class PowerCalculatorClassOmicron(threading.Thread):
class PowerCalculatorClassOmicron(object):
    """ Calculate the wanted amount of current.
    """
    def __init__(self, ramp=None):
        #threading.Thread.__init__(self)
        self.error = ''
        self.comms = {}
        self.comms['temperature'] = DateDataPullClient('rasppi83', 'mgw_temp', exception_on_old_data=True)
        try:
            #self.comms['temperature sample'] = DateDataPullClient('rasppi98', 'omicron_TPD_sample_temp', exception_on_old_data=True, port=9002, timeout=0.1)
            self.comms['temperature sample'] = DateDataPullClient('10.54.7.193', 'omicron_TPD_sample_temp', exception_on_old_data=True, port=9002, timeout=0.1)
        except socket.timeout:
            self.comms['temperature sample'] = None
            self.error = 'socket'
        #self.comms['pressure'] = DateDataPullClient('rasppi98', 'omicron_pvci_pull')
        self.values = {}
        self.values['pid'] = 0
        self.values['setpoint'] = None
        self.values['temperature'] = None
        self.values['old_temperature'] = -9998
        self.values['time'] = 0
        self.start_values = {}
        self.start_values['time'] = -9999
        self.start_values['temperature'] = -9999
        self.zero = 0 # Offset for PID control
        self.pid = PID.PID(pid_p=0.2, pid_i=0.05, pid_d=0)
        self.quit = False
        #self.wait_time = 0.05
        if ramp <= 0:
            raise ValueError('Ramp parameter \"{}\" not larger than zero'.format(ramp))
        self.ramp = ramp
        self.get_temperature()
        #time.sleep(0.2)

    def get_temperature(self):
        """Updates the temperature (Kelvin)"""

        t0 = time.time()
        while time.time() - t0 < 1.0: # Timeout on old values
            # Restart socket client
            if self.comms['temperature sample'] is None:
                try:
                    self.comms['temperature sample'] = DateDataPullClient('omicron-ms.clients.net.dtu.dk', 'omicron_TPD_sample_temp', exception_on_old_data=True, port=9002, timeout=0.1)
                except socket.timeout:
                    self.comms['temperature sample'] = None
                    self.error = 'socket' # Broadcasting socket is offline
                    return None
            # Get temperature from DateDataPullSocket
            try:
                ret = self.comms['temperature sample'].get_field('omicron_T_sample')
                self.error = ''
                if ret[1] == -1000:
                    self.error = 'open'
                    return None
                elif ret[1] == -2000:
                    self.error = 'cjc error'
                    return None
            except socket.timeout:
                # Broadcasting client may have crashed - kill client
                self.comms['temperature sample'] = None
                continue
            #except ValueError as e:
            #    LOGGER.error('Raising valueerror.', exc_info=True)
            #    raise ValueError('Error in DateDataPullClient. Try and restart DateDataPullSocket.', e)

            # Check for old data
            if ret[0] != self.values['time']:
                #print(5)
                self.values['temperature'] = ret[1]
                self.values['time'] = ret[0]
                # For testing:
                #if time.time() - self.start_values['time'] > 10:
                #    self.values['temperature'] += (time.time() - self.start_values['time'] - 10)*2.
                self.error = ''
                return self.values['temperature']
            else:
                self.error = 'old data'
                return None
        LOGGER.warning('{:.2} s ramp runtime. get_temperature timeout: returning None'.format(time.time()-self.start_values['time']))
        self.error = 'timeout'
        return None

    def initialize(self):
        """Prepare calculator"""
        self.start_values['time'] = time.time()
        self.start_values['temperature'] = self.get_temperature()
        self.values['setpoint'] = self.start_values['temperature']
        self.pid.reset()

    def stop(self):
        """Signal calculator is not in use"""
        self.start_values['time'] = None
        self.start_values['temperature'] = None
        self.values['setpoint'] = None
        self.pid.reset()

    def get_setpoint(self):
        """Get updated setpoint"""
        temp = None
        counter = 0
        while temp is None:
            temp = self.get_temperature()
            self.values['setpoint'] = (time.time() - self.start_values['time']) * self.ramp + self.start_values['temperature']
            if not temp is None:
                out_pid = self.pid.get_output(temp, self.values['setpoint'])
                return out_pid + self.zero
            elif temp is None and self.error == 'old data':
                if counter > 5:
                    LOGGER.warning('Temperature error: returning PID output (setpoint) as None. ' + self.error)
                    return None
                counter += 1
                continue
            else:
                LOGGER.warning('Temperature error: returning PID output (setpoint) as None. ' + self.error)
                return None

    def error(self):
        """ Print PID error information """
        print(self.pid.error[1])
        print(self.pid.last_error[1])
        print(self.pid.int_error)

    #def run(self):
    #    """Main thread activity: continuously updates the setpoint from the newest values"""
    #    while not self.quit:
    #        #time0 = time.time()
    #        self.get_setpoint()
    #        self.get_temperature()
    #        self.values['pid'] = self.pid.get_output(self.values['temperature'])
    #        #print(time.time() - time0)
    #        #time.sleep(self.wait_time)

    #def reset(self):
    #    """Reset PID conditions """
    #    self.start_values['time'] = time.time()
    #    self.start_values['temperature'] = self.get_temperature()
    #    self.get_setpoint()
    #    self.pid.error = 0
    #    self.pid.int_err = 0

    #def stop(self):
    #    """Close down thread by supplying FALSE to while loop in \"run\""""
    #    self.quit = True

if __name__ == '__main__':
    calc = PowerCalculatorClassOmicron(ramp=1)
    time.sleep(1)

    calc.initialize()
    for i in range(1000):
        print(i, 999, calc.get_setpoint())
