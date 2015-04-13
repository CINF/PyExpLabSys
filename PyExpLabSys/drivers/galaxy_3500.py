# pylint: disable=C0325
import telnetlib

class Galaxy3500():
    """ Interface driver for a Galaxy3500 UPS. """
    def __init__(self, hostname):
        self.ups_handle = telnetlib.Telnet(hostname)
        self.ups_handle.expect([': '])
        self.ups_handle.write('apc' + '\r')
        self.ups_handle.expect([': '])
        self.ups_handle.write('apc' + '\r')
        self.ups_handle.expect(['apc>'])

    def comm(self, command, keyword = ''):
        """ Send a command to the ups """
        self.ups_handle.write(command + '\r')
        echo = self.ups_handle.expect(['\r'])[2]
        assert(echo == command + '\r')
        code = self.ups_handle.expect(['\r'])[2]
        assert('E000' in code)
        return_string = self.ups_handle.expect(['apc>'])[2]

        if keyword is not None:
            pos = return_string.find(keyword)
            length = len(keyword + ':')
            return_string = return_string[pos + length:-5]
        else:
            return_string = return_string[1:-5]
        return return_string

    def alarms(self):
        """ Return list of active alarms """
        warnings = self.comm('alarmcount -p warning', 'WarningAlarmCount')
        nr_warnings = int(warnings)
        critical = self.comm('alarmcount -p critical', 'CriticalAlarmCount')
        nr_criticals = int(critical)
        return nr_warnings, nr_criticals

    def battery_charge(self):
        """ Return the battery charge state """
        charge_string = self.comm('detstatus -soc', 'Battery State Of Charge')
        charge_value = float(charge_string.strip()[:-2]) # Remove % sign
        return charge_value


if __name__ == '__main__':
    UPS = Galaxy3500('ups-b312')
    print UPS.alarms()
    print UPS.battery_charge()
