import sys
sys.path.append('../')
import agilent_34972A as multiplexer

def read_voltages():
    mux = multiplexer.Agilent34972ADriver(name='tof-agilent-34972a')
    mux.set_scan_list(['101,102,103,104,105,106,107,108,109,110,111,112,113,114,115'])

    values = mux.read_single_scan()

    A2    = values[11] * 10
    Def   = values[8]  * 1000
    Focus = values[7]  * 1000
    Liner = values[6]  * 1000
    MCP   = values[5]  * 1000
    R1    = values[9]  * 1000
    R2    = values[10] * 1000
    Lens_A = values[0] * 100
    Lens_B = values[1] * 100
    Lens_C = values[2] * 100
    Lens_D = values[3] * 100
    Lens_E = values[4] * 100

    voltages  = ''
    voltages += 'A2:' + str(A2) + ' '
    voltages += 'Def:' + str(Def) + ' '
    voltages += 'Focus:' + str(Focus) + ' '
    voltages += 'Liner:' + str(Liner) + ' '
    voltages += 'MCP:' + str(MCP) + ' '
    voltages += 'R1:' + str(R1) + ' '
    voltages += 'R2:' + str(R2) + ' '
    voltages += 'Lens_A:' + str(Lens_A) + ' '
    voltages += 'Lens_B:' + str(Lens_B) + ' '
    voltages += 'Lens_C:' + str(Lens_C) + ' '
    voltages += 'Lens_D:' + str(Lens_D) + ' '
    voltages += 'Lens_E:' + str(Lens_E) + ' '

    return voltages


if __name__ == '__main__':
    print read_voltages()
