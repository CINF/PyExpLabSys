from time import sleep
from pprint import pprint
#from PyExpLabSys.drivers.dataq_binary import DI1110
from PyExpLabSys.drivers.dataq_comm import DataQ
from PyExpLabSys.common.sockets import DateDataPullSocket


if __name__ == '__main__':
    #dataq = DI1110('/dev/serial/by-id/usb-DATAQ_Instruments_Generic_Bulk_Device_599C2B33_DI-1110-if00-port0')
    dataq = DataQ('/dev/serial/by-id/usb-0683_1450-if00')

    # For DataQ DI1110:
    #dataq.sample_rate(1000)
    #sleep(0.2)
    #dataq.scan_list([0, 1])
    #sleep(0.2)
    #dataq.start()
    #try:
    #    while True:
    #        dataq.clear_buffer()
    #        sleep(0.2)
    #        data = dataq.read()
    #        string = 'Channel {}: {: >6.4} V\tChannel {}: {: >6.4} V'.format(data[0]['channel'], data[0]['value'], data[1]['channel'], data[1]['value'])
    #        #string = str(data[1]['value'])
    #        print(string)
    #        for i in range(len(data)):
    #            datasocket.set_point_now(CODENAMES[i], data[i]['value'])
    #except KeyboardInterrupt:
    #    dataq.stop()
    #    datasocket.stop()

    # For DataQ DI-145:
    dataq.add_channel(1) # Current
    dataq.add_channel(2) # Voltage

    CODENAMES = ['hv_psu_current', 'hv_psu_voltage']

    # Pull socket
    datasocket = DateDataPullSocket('hv_psu', CODENAMES, timeouts=4, port=9002)
    datasocket.start()

    string = 'Channel {}: {: >6.4} V\tChannel {}: {: >6.4} V'
    dataq.start_measurement()
    sleep(1)
    while True:
        try:
            result = dataq.read_measurements()
        except KeyboardInterrupt:
            dataq.stop_measurement()
            datasocket.stop()
            break
        except:
            print('dataq error')
            dataq.stop_measurement()
            raise
        current = result[1]
        voltage = result[2]
        datasocket.set_point_now('hv_psu_current', current)
        datasocket.set_point_now('hv_psu_voltage', voltage)
        print(string.format(1, current, 2, voltage))
        try:
            sleep(0.18)
        except KeyboardInterrupt:
            dataq.stop_measurement()
            datasocket.stop()

