import omronfins.finsudp as finsudp
from omronfins.finsudp import datadef


class MoorfieldMinilab:
    def __init__(self):
        self.fins = finsudp.FinsUDP(0, 170)
        # ret = fins.open('192.168.1.99', 9600)
        self.fins.open('192.168.1.99', 9600)
        self.fins.set_destination(dst_net_addr=0, dst_node_num=99, dst_unit_addr=0)

    def _read_value(self, addr):
        # Todo: Possibly we need to read more mem_areas and more datatypes
        # I am a bit uncertain, if datatype is a unique function of mem_area
        ret, value = self.fins.read_mem_area(
            mem_area=datadef.DM_WORD, addr=addr, bit=0, num=2, dtype=datadef.FLOAT
        )
        if ret > 0:
            print('error when reading from {}'.format(address))
        return value

    def read_mfc(self, mfc_number):
        if mfc_number == 1:
            addr_setpoint = 266  # Apprantly also 464 and 1214
            addr_actual = 1103  # Apprantly also 1202
        elif mfc_number == 2:
            addr_setpoint = 328  # Apprantly also 470 and 1216
            addr_actual = 1105  # Apprantly also 1204

        setpoint = self._read_value(addr=addr_setpoint)
        actual = self._read_value(addr=addr_actual)
        return_val = {'setpoint': setpoint, 'actual': actual}
        return return_val
    
    def read_full_range_gauge(self):
        addr = 397
        value = self._read_value(addr=addr)
        return value

    def read_baratron_gauge(self):
        addr = 1200  # apprantly also 1376
        value = self._read_value(addr=addr)
        return value


if __name__ == '__main__':
    ML = MoorfieldMinilab()
    print(ML.read_full_range_gauge())
    print(ML.read_baratron_gauge())

    print(ML.read_mfc(1))
    print(ML.read_mfc(2))
