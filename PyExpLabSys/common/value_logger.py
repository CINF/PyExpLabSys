import threading
import time

class ValueLogger(threading.Thread):
    """ Read a continuously updated values and decides
    whether it is time to log a new point """
    def __init__(self, value_reader, maximumtime=600, low_comp=None,
                 comp_type = 'lin', comp_val = 1, channel = None):
        threading.Thread.__init__(self)
        self.daemon = True
        self.valuereader = value_reader
        self.value = None
        self.channel = channel
        self.maximumtime = maximumtime
        self.status = {}
        self.compare = {}
        self.last = {}
        self.compare['type'] = comp_type
        self.compare['val'] = comp_val
        self.compare['low_comp'] = low_comp
        self.status['quit'] = False
        self.status['trigged'] = False
        self.last['time'] = 0
        self.last['val'] = 0

    def read_value(self):
        """ Read the current value """
        return self.value

    def read_trigged(self):
        """ Ask if the class is trigged """
        return self.status['trigged']

    def clear_trigged(self):
        """ Clear trigger """
        self.status['trigged'] = False

    def run(self):
        while not self.status['quit']:
            time.sleep(1)
            if self.channel is None:
                self.value = self.valuereader.value()
            else:
                self.value = self.valuereader.value(self.channel)
            time_trigged = ((time.time() - self.last['time'])
                            > self.maximumtime)

            try:
                if self.compare['type'] == 'lin':
                    val_trigged = not (self.last['val'] - self.compare['val']
                                       < self.value
                                       < self.last['val'] + self.compare['val'])
                if self.compare['type'] == 'log':
                    val_trigged = not (self.last['val'] *
                                       (1 - self.compare['val'])
                                       < self.value
                                       < self.last['val'] *
                                       (1 + self.compare['val']))
            except UnboundLocalError:
                #Happens when value is not yes ready from reader
                val_trigged = False
                time_trigged = False

            # Will only trig on value of value is larger than low_comp
            if self.compare['low_comp'] is not None:
                if self.value < self.compare['low_comp']:
                    val_trigged = False

            if (time_trigged or val_trigged) and (self.value is not None):
                self.status['trigged'] = True
                self.last['time'] = time.time()
                self.last['val'] = self.value
