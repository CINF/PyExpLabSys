import threading
import time

class ValueLogger(threading.Thread):
    """ Read a continuously updated values and decides
    whether it is time to log a new point """
    def __init__(self, value_reader, maximumtime=600,
                 comp_type = 'lin', comp_val = 1):
        threading.Thread.__init__(self)
        self.valuereader = value_reader
        self.value = None
        self.maximumtime = maximumtime
        self.status = {}
        self.compare = {}
        self.last = {}
        self.compare['type'] = comp_type
        self.compare['val'] = comp_val
        self.status['quit'] = False
        self.status['trigged'] = False
        self.last['time'] = 0
        self.last['val'] = 0

    def read_value(self):
        """ Read the current value """
        return(self.value)

    def read_trigged(self):
        """ Ask if the class is trigged """
        return(self.status['trigged'])

    def clear_trigged(self):
        """ Clear trigger """
        self.status['trigged'] = False

    def run(self):
        while not self.status['quit']:
            time.sleep(1)
            self.value = self.valuereader.value()
            time_trigged = ((time.time() - self.last['time'])
                            > self.maximumtime)
            # TODO: Here we should check for the comp_type
            val_trigged = not (self.last['val'] - self.compare['val']
                               < self.value
                               < self.last['val'] + self.compare['val'])
            if (time_trigged or val_trigged) and (self.value > 0):
                self.status['trigged'] = True
                self.last['time'] = time.time()
                self.last['val'] = self.value
