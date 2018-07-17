"""Run a heat ramp for the Omicron TPD stage """
import time
import threading
#import PyExpLabSys.auxiliary.pid as PID
import pid as PID
#from fug import FUGNTN140Driver as FUG
#import PyExpLabSys.drivers.fug.FUGNTN140Driver as FUG
from PyExpLabSys.common.socket_clients import DateDataPullClient
#from pull import DateDataPullClient

class PowerCalculatorClassOmicron(threading.Thread):
    """ Calculate the wanted amount of current.
    """
    def __init__(self, ramp=None):
        threading.Thread.__init__(self)
        self.comms = {}
        self.comms['temperature'] = DateDataPullClient('rasppi83', 'mgw_temp')
        #self.comms['pressure'] = DateDataPullClient('rasppi98', 'omicron_pvci_pull')
        self.values = {}
        self.values['pid'] = 0
        self.values['setpoint'] = None
        self.values['temperature'] = None
        self.values['time'] = 0
        self.start_values = {}
        self.start_values['time'] = -9999
        self.start_values['temperature'] = -9999
        self.pid = PID.PID(pid_p=0.2, pid_i=0.05, pid_d=0, p_max=10)
        self.quit = False
        self.wait_time = 0.05
        if ramp <= 0:
            raise ValueError('Ramp parameter \"{}\" not larger than zero'.format(ramp))
        self.ramp = ramp
        time.sleep(0.2)
        #print('Power Calculator started\n')


    def get_temperature(self):
        """Updates the temperature (Kelvin)"""
        self.values['temperature'] = self.comms['temperature'].get_field('omicron_tpd_sample_temperature')[1]
        return self.values['temperature']


    def get_setpoint(self):
        time_lapse = time.time() - self.start_values['time']
        self.values['time'] = time_lapse
        self.values['setpoint'] = self.ramp * time_lapse + self.start_values['temperature']
        return self.pid.update_setpoint(self.values['setpoint'])


    def run(self):
        """Main thread activity: continuously updates the setpoint from the newest values"""
        while not self.quit:
            #time0 = time.time()
            self.get_setpoint()
            self.get_temperature()
            self.values['pid'] = self.pid.get_output(self.values['temperature'])
            #print(time.time() - time0)
            #time.sleep(self.wait_time)

    def reset(self):
        """Reset PID conditions """
        self.start_values['time'] = time.time()
        self.start_values['temperature'] = self.get_temperature()
        self.get_setpoint()
        self.pid.error = 0
        self.pid.int_err = 0

    def stop(self):
        """Close down thread by supplying FALSE to while loop in \"run\""""
        self.quit = True

def main():
    """Main loop creating a heat ramp """
    PowerCalculator.reset()
    try:
        while not PowerCalculator.pid.ID_max:
            setpoint = PowerCalculator.values['pid']+REFERENCE_CURRENT
            PowerSupply.set_current(setpoint)
            time.sleep(0.1)
            current = PowerSupply.monitor_current()
            print('Lapsed time: {:.4} s, Setpoint: {}, Current: {}, error: ({},{})'.format(PowerCalculator.values['time'], setpoint, current, PowerCalculator.pid.error, PowerCalculator.pid.int_err))
            if (setpoint >= STOP_CURRENT) or (PowerCalculator.values['temperature'] >= STOP_TEMPERATURE):
                print('Stop condition reached. Halting heat ramp..')
                PowerCalculator.pid.ID_max = True
                for i in range(10):
                    print(10-i)
                    time.sleep(1)
                print('Closing down..\n')
        else:
            PowerCalculator.stop()
            PowerSupply.stop()
            print('Connections closed succesfully\n')
    except KeyboardInterrupt:
        PowerCalculator.stop()
        PowerSupply.stop()
        print('Heat ramp was forced to stop (CTRL+C)\n')
    except:
        PowerCalculator.stop()
        PowerSupply.stop()
        raise


if __name__ == '__main__':
    calc = PowerCalculatorClassOmicron(ramp=1)
    time.sleep(2)
    calc.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        calc.stop()
