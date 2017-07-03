# pylint: disable=C0325
""" Python interface for Galaxy 3500 UPS. The driver uses the
telnet interface of the device.
"""
from __future__ import print_function
import telnetlib
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

class Galaxy3500(object):
    """ Interface driver for a Galaxy3500 UPS. """
    def __init__(self, hostname):
        self.status = {}
        self.ups_handle = telnetlib.Telnet(hostname)
        self.ups_handle.expect([b': '])
        self.ups_handle.write(b'apc' + b'\r')
        self.ups_handle.expect([b': '])
        self.ups_handle.write(b'apc' + b'\r')
        self.ups_handle.expect([b'apc>'])

    def comm(self, command, keywords=None):
        """ Send a command to the ups """
        self.ups_handle.write(command.encode('ascii') + b'\r')
        echo = self.ups_handle.expect([b'\r'])[2]
        assert(echo == command.encode('ascii') + b'\r')
        code = self.ups_handle.expect([b'\r'])[2]
        assert('E000' in code.decode())
        output = self.ups_handle.expect([b'apc>'])[2]
        output = output.decode()

        if keywords is not None:
            return_val = {}
            for param in list(keywords):
                pos = output.find(param)
                line = output[pos + len(param) + 1:pos + len(param) + 8].strip()
                for i in range(0, 3):
                    try:
                        value = float(line[:-1 * i])
                        break
                    except ValueError:
                        pass
                return_val[param] = value
        else:
            return_val = output[1:-5]
        return return_val

    def alarms(self):
        """ Return list of active alarms """
        warnings = self.comm('alarmcount -p warning', ['WarningAlarmCount'])
        criticals = self.comm('alarmcount -p critical', ['CriticalAlarmCount'])
        warnings_value = int(warnings['WarningAlarmCount'])
        criticals_value = int(criticals['CriticalAlarmCount'])
        self.status['WarningAlarmCount'] = warnings_value
        self.status['CriticalAlarmCount'] = criticals_value
        return (warnings_value, criticals_value)

    def battery_charge(self):
        """ Return the battery charge state """
        keyword = 'Battery State Of Charge'
        charge = self.comm('detstatus -soc', [keyword])
        self.status[keyword] = charge[keyword]
        return charge[keyword]

    def temperature(self):
        """ Return the temperature of the UPS """
        keyword = 'Internal Temperature'
        temp = self.comm('detstatus -tmp', [keyword])
        self.status[keyword] = temp[keyword]
        return temp[keyword]

    def battery_status(self):
        """ Return the battery voltage """
        params = ['Battery Voltage', 'Battery Current']
        output = self.comm('detstatus -bat', params)
        for param in params:
            self.status[param] = output[param]
        return output

    def output_measurements(self):
        """ Return status of the device's output """
        params = ['Output Voltage L1', 'Output Voltage L2', 'Output Voltage L3',
                  'Output Frequency', 'Output Watts Percent L1',
                  'Output Watts Percent L2', 'Output Watts Percent L3',
                  'Output VA Percent L1', 'Output VA Percent L2',
                  'Output VA Percent L3', 'Output kVA L1',
                  'Output kVA L2', 'Output kVA L3', 'Output Current L1',
                  'Output Current L2', 'Output Current L3']
        output = self.comm('detstatus -om', params)
        for param in params:
            self.status[param] = output[param]
        return output

    def input_measurements(self):
        """ Return status of the device's output """
        params = ['Input Voltage L1', 'Input Voltage L2', 'Input Voltage L3',
                  'Input Frequency', 'Bypass Input Voltage L1',
                  'Bypass Input Voltage L2', 'Bypass Input Voltage L3',
                  'Input Current L1', 'Input Current L2', 'Input Current L3']
        output = self.comm('detstatus -im', params)
        for param in params:
            self.status[param] = output[param]
        return output

if __name__ == '__main__':
    UPS = Galaxy3500('ups-b312')
    print(UPS.alarms())
    print(UPS.battery_charge())
    print(UPS.output_measurements())
    print(UPS.input_measurements())
    print(UPS.battery_status())
    print(UPS.temperature())
    print('---')
    print(UPS.status)
