"""
Log up to eight analog signals using up to two ADS1115 analog inputs.
"""
import time
import threading

import ADS1x15

from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver

from read_config import read_configuration



class Reader(threading.Thread):
    """ Read values from the mercury controller """
    def __init__(self, adc_mapping: dict) -> None:
        threading.Thread.__init__(self)
        self.name = 'Reader Thread'
        self.config = read_configuration('config.toml')
        
        self.adc_mapping = adc_mapping
        self.adcs = {}
        self.values = {}
        for addr, adc_map in adc_mapping.items():
            self.adcs[addr] = ADS1x15.ADS1115(1, address=addr)
            self.adcs[addr].setDataRate(0)
            # Todo: Consider to implement auto-range gain
            self.adcs[addr].setGain(2)  # TODO!

            for codename in adc_map.keys():
                self.values[codename] = -1                
                
        self.pullsocket = DateDataPullSocket(
            self.config['description'],
            list(self.values.keys()),
            timeouts=[10] * len(self.values),
            port=9000
        )
        self.pullsocket.start()
        self.livesocket = LiveSocket(
            self.config['description'] + 'Live',
            list(self.values.keys())
        )
        self.livesocket.start()
        self.quit = False
        self.ttl = 50

    def value(self, codename):
        """ Read a stored value if TTL is valid """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            print('TTL is out! Stopping')
            self.quit = True
            return_val = None
        return_val = self.values[codename]
        return return_val

    def _update_values(self):
        """
        Iterate over alle ADCs and channels and measure values
        """
        for addr, adc_mapping in self.adc_mapping.items():
            adc = self.adcs[addr]
            # prefix = adc_mapping['prefix']
            for codename, parameters in adc_mapping.items():
                # codename = prefix + '_' + parameter
                channel = parameters[0]
                offset =  parameters[1]
                scale =  parameters[2]

                adc.requestADC(channel)
                time.sleep(0.15)  # TODO!
                voltage_raw = adc.getValue()
                voltage = adc.toVoltage(voltage_raw)

                if codename in self.config.get('RTDs', {}):
                    v_ex = self.config['RTDs'][codename]['v_ex']
                    r_shunt = self.config['RTDs'][codename]['r_shunt']
                    value  = r_shunt * voltage / (v_ex - voltage)
                else:
                    value = voltage
                scaled_result = scale * value + offset
                self.values[codename] = scaled_result

                self.pullsocket.set_point_now(codename, scaled_result)
                self.livesocket.set_point_now(codename, scaled_result)

    def run(self):
        while not self.quit:
            self.ttl = 100
            # time.sleep(0.5)
            self._update_values()


class Logger():
    def __init__(self):        
        self.config = read_configuration('config.toml')
        self.credentials = read_configuration('credentials.toml')

        self.loggers = {}

        codenames = {}
        adc_mapping = {}
        for address_str, channel_config in self.config['ADC_mapping'].items():
            addr = int(address_str, 16)
            adc_mapping[addr] = {}
            for codename, config in channel_config.items():
                codenames[codename] = config[3]
                adc_mapping[addr][codename] = [config[0], config[1], config[2]]

        self.reader = Reader(adc_mapping=adc_mapping)
        self.reader.start()

        self.db_logger = ContinuousDataSaver(
            continuous_data_table=self.config['database']['table'],
            username=self.credentials['user'],
            password=self.credentials['passwd'],
            measurement_codenames=codenames.keys()
        )
        self.db_logger.name = 'DB Logger Thread'
        self.db_logger.start()

        for codename, comp_val in codenames.items():
            self.loggers[codename] = ValueLogger(
                self.reader,
                comp_val=comp_val,
                comp_type='lin',
                maximumtime=600,
                channel=codename,
            )
            self.loggers[codename].name = 'Logger_thread_{}'.format(codename)
            self.loggers[codename].start()

    def main(self):
        """
        Main function
        """
        time.sleep(5)
        while self.reader.is_alive():
            time.sleep(5)
            for name, data_logger in self.loggers.items():
                value = data_logger.read_value()
                if data_logger.read_trigged():
                    msg = '{} is logging value: {}'
                    print(msg.format(name, value))
                    self.db_logger.save_point_now(name, value)
                    data_logger.clear_trigged()


if __name__ == '__main__':
    logger = Logger()
    logger.main()
