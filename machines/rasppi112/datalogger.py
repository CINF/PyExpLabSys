from drivers import DI2008
from sockets import GC_data_socket, pressure_socket
import time

def mean(some_list):
    return sum(some_list)/len(some_list)

data_sock = GC_data_socket()
pressure_sock = pressure_socket()

dataq = DI2008('/dev/ttyACM0')
for n, Vdc in zip([1,2,3,4,5,8],[10.,0.1,0.1,10.,10.,10.]): #1 is ready, 2 and 4 is FID, 3 and 5 is TCD
    dataq.add_voltage_analog_channel(n, voltage = Vdc)
dataq.start()

print('All devices initialized')
retention_zero = time.time()
retention_time_cache = []
FID_lowV_cache = []
FID_highV_cache = []
TCD_lowV_cache = []
TCD_highV_cache = []

try:
    while True:
        loop_time = time.time()
        raw_data = dataq.read()
        data_sock.set_point_now('ready_voltage', [raw_data[1]])
        pressure_sock.set_point_now([raw_data[8]*2.052+0.996])
        #pressure_sock.set_point_now([raw_data[8]])
        #pressure_sock.set_point_now([raw_data[8]*2.075+1.010]) #old calibration
        retention_time_cache.append(round(time.time()-retention_zero,3))
        FID_lowV_cache.append(raw_data[2])
        FID_highV_cache.append(raw_data[4])
        TCD_lowV_cache.append(raw_data[3])
        TCD_highV_cache.append(raw_data[5])
        if len(retention_time_cache) == 8: #averaging over 8 points
            data_sock.set_point_now('retention_time', [round(retention_time_cache[-1],3)])
            data_sock.set_point_now('FID low V', [mean(FID_lowV_cache)])
            data_sock.set_point_now('FID high V', [mean(FID_highV_cache)])
            data_sock.set_point_now('TCD low V', [mean(TCD_lowV_cache)])
            data_sock.set_point_now('TCD high V', [mean(TCD_highV_cache)])
            retention_time_cache = retention_time_cache[1:]
            FID_lowV_cache = FID_lowV_cache[1:]
            FID_highV_cache = FID_highV_cache[1:]
            TCD_lowV_cache = TCD_lowV_cache[1:]
            TCD_highV_cache = TCD_highV_cache[1:]
        try:
            time.sleep(0.006-time.time()+loop_time) #0.006 is the lowest update value.
        except:
            continue
except KeyboardInterrupt:
    data_sock.stop()

