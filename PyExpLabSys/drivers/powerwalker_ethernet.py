import datetime
import paramiko


class PowerWalkerEthernet(object):
    """
    This driver uses the fact that the PowerWalker allows ssh-access,
    and thus gives access the actual binary files that reads the internal
    values. SNMP could also be used, but apparently most values miss a
    digit compared to the internal tools.
    """
    def __init__(self, ip_address, read_old_events=True):
        if read_old_events:
            self.latest_event = datetime.datetime.min
        else:
            self.latest_event = datetime.datetime.now()
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(ip_address, username='root',
                         password='12345678', look_for_keys=False)

    def _read_static_data(self):
        """
        Reads combined static information about the unit, this is
        traditionally returned as two seperate calls, thus this is
        considered a private function.
        """
        command = '/var/www/html/web_pages_Galleon/cgi-bin/baseInfo.cgi'
        stdin, stdout, stderr = self.ssh.exec_command(command, timeout=0.75)
        raw_lines = stdout.readlines()

        lines = []
        for line in raw_lines:
            # lines.append(line.strip())  # Removed line filtering to preserve indexes,
            lines.append(line.strip())    # because those lines are not always empty

        nominal_input = int(lines[5][0:3])  # was index 4
        nominal_output = int(lines[5][4:])  # was index 4
        values = {
            'model': lines[3],  # was index 2
            'version': lines[7],  # was index 6
            'nominal_input_voltage': nominal_input,
            'nominal_output_voltage': nominal_output,
            'nominal_output_frequency': int(lines[11]) / 10.0,  # was index 10
            'rated_battery_voltage': int(lines[13]) / 10.0,  # was index 12
            'rated_va': int(lines[9]),  # was index 8
            'rated_output_current': int(lines[12]) / 10.0  # was index 11
        }
        return values

    def device_information(self):
        statics = self._read_static_data()
        information = {
            'company': 'Power Walker',
            'model': statics['model'],
            'version': statics['version']
        }
        return information

    def device_ratings(self):
        statics = self._read_static_data()
        ratings = {
            'rated_voltage': statics['nominal_output_voltage'],
            'rated_current': statics['rated_output_current'],
            'battery_voltage': statics['rated_battery_voltage'],
            'rated_frequency': statics['nominal_output_frequency']
        }
        return ratings

    def device_status(self):
        command = '/var/www/html/web_pages_Galleon/cgi-bin/realInfo.cgi'
        stdin, stdout, stderr = self.ssh.exec_command(command, timeout=0.75)
        raw_lines = stdout.readlines()

        lines = []
        for line in raw_lines:
            # lines.append(line.strip())  # Removed line filtering to preserve indexes,
            lines.append(line.strip())    # because those lines are not always empty

        status = []
        if not lines[2] == 'Line Mode':  # was index 1
            status.append('Utility Fail')

        values = {
            'input_voltage': int(lines[15]) / 10.0,  # was index 12
            'output_voltage': int(lines[18]) / 10.0,  # was index 15
            'output_current': int(lines[38]) / 10.0,  # was index 35
            'input_frequency': int(lines[14]) / 10.0,  # was index 11
            'battery_voltage': int(lines[11]) / 10.0,  # was index 8
            'temperature': int(lines[3]) / 10.0,  # was index 2
            'status': status,
            'battery_capacity': int(lines[12]),  # was index 9
            'remaining_battery': lines[13],  # was index 10
            'output_frequency': int(lines[17]) / 10.0,  # was index 14
            'load_level': int(lines[20])  # was index 17
        }
        return values

    def read_events(self, only_new=False):
        command = 'cd /var/log/eventlog; cat "$(ls -1rt | tail -n1)"'
        stdin, stdout, stderr = self.ssh.exec_command(command, timeout=0.75)
        raw_lines = stdout.readlines()

        if len(raw_lines) < 2:
            print('PowerWalker Ethernet: Too few lines in event file')
            return None

        events = []
        for line in raw_lines[1:]:
            split_line = line.strip().split(',')
            timestamp = datetime.datetime.strptime(split_line[0],
                                                   '%Y/%m/%d %H:%M:%S')
            if only_new and timestamp <= self.latest_event:
                continue
            event = {
                'timestamp': timestamp,
                'event': split_line[1],
                'source': split_line[2]
            }
            events.append(event)
            self.latest_event = timestamp
        return events

if __name__ == '__main__':
    pw = PowerWalkerEthernet(ip_address='192.168.2.100')

    print(pw.device_status())
    print()
    print()
    print(pw._read_static_data())
    print()
    print()
    events = pw.read_events()
    for event in events:
        print(event)
