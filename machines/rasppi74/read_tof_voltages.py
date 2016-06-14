""" Read the voltages from the analog voltage supply for the TOF """
import PyExpLabSys.drivers.agilent_34972A as multiplexer

def read_voltages():
    """ Do the reading """
    mux = multiplexer.Agilent34972ADriver(name='tof-agilent-34972a')
    mux.set_scan_list(['101,102,103,104,105,106,107,108,109,110,111,112'])

    values = mux.read_single_scan()

    a2 = values[11] * 10 / 0.9911
    deflection = values[8] * 1000 / 0.9936
    focus = values[7]  * 1000 / 0.9925
    liner = values[6]  * 1000 / 0.9938
    mcp = values[5]  * 1000 / 0.9943
    r1 = values[9]  * 1000 / 0.9931
    r2 = values[10] * 1000 / 0.9875
    lens_A = values[0] * 100
    lens_B = values[1] * 100
    lens_C = values[2] * 100
    lens_D = values[3] * 100
    lens_E = values[4] * 100

    voltages = ''
    voltages += 'A2:' + str(a2) + ' '
    voltages += 'Def:' + str(deflection) + ' '
    voltages += 'Focus:' + str(focus) + ' '
    voltages += 'Liner:' + str(liner) + ' '
    voltages += 'MCP:' + str(mcp) + ' '
    voltages += 'R1:' + str(r1) + ' '
    voltages += 'R2:' + str(r2) + ' '
    voltages += 'Lens_A:' + str(lens_A) + ' '
    voltages += 'Lens_B:' + str(lens_B) + ' '
    voltages += 'Lens_C:' + str(lens_C) + ' '
    voltages += 'Lens_D:' + str(lens_D) + ' '
    voltages += 'Lens_E:' + str(lens_E) + ' '

    return voltages


if __name__ == '__main__':
    print read_voltages()
