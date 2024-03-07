import omronfins.finsudp as finsudp
from omronfins.finsudp import datadef


class MoorfieldMinilab:
    def __init__(self, mapping):
        self.mapping = mapping

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
        addr_setpoint = None
        addr_actual = None
        if mfc_number == 1:
            addr_setpoint = self.mapping.get('mfc_1_setpoint')
            addr_actual = self.mapping.get('mfc_1_flow')
        elif mfc_number == 2:
            addr_setpoint = self.mapping.get('mfc_2_setpoint')
            addr_actual = self.mapping.get('mfc_2_flow')
        elif mfc_number == 3:
            addr_setpoint = self.mapping.get('mfc_3_setpoint')
            addr_actual = self.mapping.get('mfc_3_flow')

        setpoint = None
        if addr_setpoint is not None:
            setpoint = self._read_value(addr=addr_setpoint)

        actual = None
        if addr_actual is not None:
            actual = self._read_value(addr=addr_actual)
        return_val = {'setpoint': setpoint, 'actual': actual}
        return return_val

    def read_full_range_gauge(self):
        addr = self.mapping['full_range_pressure']
        value = self._read_value(addr=addr)
        return value

    def read_baratron_gauge(self):
        addr = self.mapping['baratron_pressure']
        value = self._read_value(addr=addr) / 1000.0
        return value

    def read_turbo_speed(self):
        value = None
        addr = self.mapping.get('turbo_speed')
        if addr is not None:
            value = self._read_value(addr=addr)
        return value

    def read_rf_values(self):
        return_val = {}
        rf_params = [
            'rf_forward_power',
            'rf_reflected_power',
            'dc_bias',
            'tune_motor',
            'load_motor',
        ]
        for param in rf_params:
            return_val[param] = None
            addr = self.mapping.get(param)
            if addr is not None:
                return_val[param] = self._read_value(addr=addr)
        return return_val

    def read_dc_psu_values(self):
        return_val = {}
        psu_params = [
            'dc_psu_voltage',
            'dc_psu_current',
            'dc_psu_power',
        ]
        for param in psu_params:
            return_val[param] = None
            addr = self.mapping.get(param)
            if addr is not None:
                return_val[param] = self._read_value(addr=addr)
        return return_val


if __name__ == '__main__':
    mapping = {
        'full_range_pressure': 398,
        'baratron_pressure': 1376,
        'mfc_1_flow': 1202,
        'mfc_1_setpoint': 1213,
        'mfc_2_flow': 1204,
        'mfc_2_setpoint': 1215,
        'mfc_3_flow': None,
        'mfc_3_setpoint': None,
        'forward_power': None,
        'reflected_power': None,
        'dc_bias': None,
        'tune_motor': None,
        'load_motor': None,
        'turbo_speed': None,
        'dc_psu_voltage': 1586,
        'dc_psu_current': 1584,
        'dc_psu_power': 1588,
    }

    ML = MoorfieldMinilab(mapping)
    print('Gauges:')
    print('Full range: ', ML.read_full_range_gauge())
    print('Baratron: ', ML.read_baratron_gauge())

    print()

    print('MFCs')
    print(ML.read_mfc(1))
    print(ML.read_mfc(2))
    print(ML.read_mfc(3))

    print()

    print('RF values')
    print(ML.read_rf_values())

    print()

    print('DC PSU values')
    print(ML.read_dc_psu_values())

    print()

    print('Turbo speed')
    print(ML.read_turbo_speed())
