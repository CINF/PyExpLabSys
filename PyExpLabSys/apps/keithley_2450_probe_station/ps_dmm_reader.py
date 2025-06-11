import threading

from PyExpLabSys.drivers.keithley_2100 import Keithley2100


class ProbeStationDMMReader(threading.Thread):
    def __init__(self, visa_string):
        threading.Thread.__init__(self)
        self.daemon = True
        self.running = True

        # TODO - Visa string should of course not be hard-codet
        self.dmm = Keithley2100(visa_string)
        self._configure()
        self.value = self.measure()

    def _configure(self):
        """
        Configure  Model 2000 used for 2-point measurement
        The unit is set up to measure on the gaurd output of
        the 2450.
        """
        self.dmm.clear_errors()
        self.dmm.measurement_function('volt:dc')
        self.dmm.measurement_range(0)
        self.dmm.integration_time(1)
        # Consider whether it makes sense to use external trigger. This would
        # sync the DMM to the 2450'ies but would also lock the measurement and
        # potentially slow down. The DMM is a sanity check that does not
        # strictly need to be 100% sync'ed to the actual measurement
        self.dmm.trigger_source(external=False)

    def measure(self):
        value = self.dmm.read()
        return value

    def run(self):
        while self.running:
            self.value = self.measure()


if __name__ == '__main__':
    import time

    reader = ProbeStationDMMReader('USB0::1510::8448::8019151::0::INSTR')
    reader.start()
    t = time.time()

    dt = time.time() - t
    while dt < 25:
        print(reader.value)
        time.sleep(0.2)
        dt = time.time() - t
    reader.running = False
