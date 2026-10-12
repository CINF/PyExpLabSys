"""
Simple driver for Kern PCB Scale.
"""

import pyvisa


class KernPCB():
    # https://docs.rs-online.com/acd0/0900766b81686741.pdf
    def __init__(self):
        rm = pyvisa.ResourceManager()
        visa_addr = 'ASRL/dev/ttyUSB0::INSTR'
        self.instr = rm.open_resource(visa_addr)
        self.read_value() # Trash first point
        
    def read_value(self):
        value_found = False
        while not value_found:
            value_raw = self.instr.read()
            stable = False
            if '\r\n' in value_raw:
                if 'g' in value_raw:
                    stable = True
                compact_value = value_raw.strip().replace('g', '')
                try:
                    value = float(compact_value)
                    value_found = True
                except:
                    pass
        return value, stable


if __name__ == '__main__':
    SCALE = KernPCB()

    while True:
        print(SCALE.read_value())
