"""
Driver for Oxford Mercury controllers
To a large extend this is implemented agains a specic device, and will
take some amount of work to generalize. Unfortunately I have access to
only a single cryostat.
"""

import time
import pyvisa


class OxfordMercury:
    def __init__(self, hostname: str) -> None:
        conn_string = 'TCPIP::{}::7020::SOCKET'.format(hostname)
        rm = pyvisa.ResourceManager('@py')
        print(conn_string)
        self.instr = rm.open_resource(conn_string)
        self.instr.read_termination = '\n'
        self.instr.write_termination = '\n'
        #    encoding='latin-1',
        self.switch_heater_turn_on_time = 0

    def _comm(self, cmd):
        error = 0
        while error > -1:
            try:
                raw_reply = self.instr.query(cmd)
                error = -1
            except ValueError:
                error += 1
                time.sleep(0.1)
                if error > 3:
                    print('Oxford read error. Try again')
        raw_reply = raw_reply.strip()
        return raw_reply

    def _read_value(
        self, uid: str, meas_type: str, keyword: str = None
    ) -> (float, str):
        if keyword is None:
            keyword = meas_type
        fields = []
        cmd = 'READ:DEV:{}:{}:SIG:{}?'.format(uid, meas_type, keyword)

        error = 0
        while len(fields) < 2:
            error = error + 1
            self.instr.write(cmd)
            raw_reply = self.instr.read(encoding='latin1')
            if error > 1:
                print('Errror!')
                print('Command:', cmd)
                print('Error is: ', error)
                print('Reply', raw_reply)
                time.sleep(0.2)
            fields = raw_reply.split(':')

        # Value is in last field
        value_raw = fields[-1]
        for i in range(1, len(value_raw)):
            try:
                float(value_raw[0 : i + 1])
            except ValueError:
                break

        value = float(value_raw[0:i])
        unit = value_raw[i:]
        return value, unit

    def read_configuration(self) -> str:
        cmd = 'READ:SYS:CAT?'
        uids = self.instr.query(cmd)
        return uids

    def read_raw(self, uid: str, meas_type: str) -> str:
        """
        Return all available information about a sensor as a string
        """
        cmd = 'READ:DEV:{}:{}?'.format(uid, meas_type)
        return self.instr.query(cmd)

    def read_temperature(self, uid: str) -> (float, str):
        value = self._read_value(uid, 'TEMP')
        return value

    def read_temperature_details(self, uid: str) -> dict:
        """
        Notice: if uid is really a magnet, these details will
        not be meaningfull, since the meta-data will be for
        magnet power, not for the temperature sensor
        """
        data = {
            'temperature': self._read_value(uid, 'TEMP'),
            'voltage': self._read_value(uid, 'TEMP', 'VOLT'),
            'current': self._read_value(uid, 'TEMP', 'CURR'),
            'resistance': self._read_value(uid, 'TEMP', 'RES'),
            'power': self._read_value(uid, 'TEMP', 'POWR'),
        }
        return data

    def read_pressure(self, uid: str) -> (float, str):
        value, unit = self._read_value(uid, 'PRES')
        return value, unit

    # TODO!!!!!
    def read_needle_valve(self, uid: str) -> (float, str):
        value, unit = self._read_value(uid, '')
        return value, unit

    def read_heater(self, uid) -> (float, str):
        value, unit = self._read_value(uid, 'HTR', 'POWR')
        return value, unit

    def read_magnetic_field(self, uid) -> (float, str):
        value, unit = self._read_value(uid, 'PSU', 'FLD')
        return value, unit

    def read_magnet_details(self, uid) -> dict:
        data = {
            'voltage': self._read_value(uid, 'PSU', 'VOLT'),
            'current': self._read_value(uid, 'PSU', 'CURR'),
            'field': self._read_value(uid, 'PSU', 'FLD'),
            # 'rate': self._read_value(uid, 'PSU', 'RFSET'),
            'target_field': self._read_value(uid, 'PSU', 'FSET'),
            'persistent_current': self._read_value(uid, 'PSU', 'PCUR'),
            'persistent_field': self._read_value(uid, 'PSU', 'PFLD'),
        }
        return data

    def switch_heater_state(self, uid, activated=None):
        if activated is not None:
            if activated:
                cmd = 'READ:DEV:{}:PSU:SIG:SWHT:ON'.format(uid)
                self._comm(cmd)
                self.switch_heater_turn_on_time = time.time()
            else:
                cmd = 'READ:DEV:{}:PSU:SIG:SWHT:OFF'.format(uid)
                self._comm(cmd)
                self.switch_heater_turn_on_time = 0
            time.sleep(1)

        cmd = 'READ:DEV:{}:PSU:SIG:SWHT?'.format(uid)
        raw_reply = self._comm(cmd)
        print(raw_reply)
        state_raw = raw_reply.split('SWHT')
        heater_on = state_raw[-1] == ':ON'
        # If heater was turned on and the software did not
        # notice, at least notice now.
        if heater_on:
            if self.switch_heater_turn_on_time == 0:
                switch_heater_turn_on_time = time.time()
        return heater_on

    def temperature_setpoint(
        self, uid: str, setpoint: float = None, rate: float = None
    ) -> float:
        if setpoint is None:
            # This code is almost identical to _read_value()....
            cmd = 'READ:DEV:{}:TEMP:LOOP:TSET?'.format(uid)
            raw_reply = self.instr.query(cmd)
            fields = raw_reply.split(':')
            value_raw = fields[-1]
            for i in range(1, len(value_raw)):
                try:
                    actual_setpoint = float(value_raw[0 : i + 1])
                except ValueError:
                    break
            return actual_setpoint

        # If we are here, we are setting a setpoint
        if setpoint > 300:
            setpoint = 5

        if rate is None:
            rate = 0.5

        cmd = 'SET:DEV:{}:TEMP:LOOP:RSET:{}K/m'.format(uid, rate)
        raw_reply = self.instr.query(cmd)
        print(cmd)
        print(raw_reply)

        # Convntion: A setpoint of 0 turns off heating entirely
        if setpoint <= 0:
            print('Turning off heater')
            cmd = 'SET:DEV:{}:TEMP:LOOP:ENAB:OFF'.format(uid)
            raw_reply = self.instr.query(cmd)
            print(raw_reply)
            # Todo check that raw_reply contains VALID
        else:
            print('Set setpoint to {}K'.format(setpoint))
            cmd = 'SET:DEV:{}:TEMP:LOOP:TSET:{}K'.format(uid, setpoint)
            raw_reply = self.instr.query(cmd)
            print(raw_reply)
            cmd = 'SET:DEV:{}:TEMP:LOOP:ENAB:ON'.format(uid)
            raw_reply = self.instr.query(cmd)
            print(raw_reply)

        return setpoint

    def b_field_setpoint(
        self, uid: str, setpoint: float = None, rate: float = None
    ) -> (float, str):
        if setpoint is None:
            # This code is almost identical to _read_value()....
            cmd = 'READ:DEV:{}:PSU:SIG:FSET?'.format(uid)
            raw_reply = self.instr.query(cmd)
            fields = raw_reply.split(':')
            value_raw = fields[-1]
            for i in range(1, len(value_raw)):
                try:
                    actual_setpoint = float(value_raw[0 : i + 1])
                except ValueError:
                    break
            return actual_setpoint

        if rate is None:
            rate = 0.1
        if rate < 0.01:
            print('Rate too low, using 0.01T/min')
            rate = 0.01
        if rate > 0.3:
            print('Rate too high, using 0.3T/min')
            rate = 0.3
        cmd = 'SET:DEV:{}:PSU:SIG:RFST:{}T/m'.format(uid, rate)
        print(cmd)
        raw_reply = self.instr.query(cmd)
        print(raw_reply)

        # If we are here, we are setting a setpoint
        if abs(setpoint) > 12:
            # Temporary safety precaution
            setpoint = 0

        if setpoint == 0:
            print('Turning off magnets')
            cmd = 'SET:DEV:{}:PSU:ACTN:RTOZ'.format(uid)
            raw_reply = self.instr.query(cmd)
            print(raw_reply)
            # Todo check that raw_reply contains VALID
        else:
            # Hold the ramp currently being performed
            cmd = 'SET:DEV:{}:PSU:ACTN:HOLD'.format(uid)
            raw_reply = self.instr.query(cmd)
            print('Set setpoint to {}T'.format(setpoint))
            # Set new setpoint
            cmd = 'SET:DEV:{}:PSU:SIG:FSET:{}T'.format(uid, setpoint)
            raw_reply = self.instr.query(cmd)
            print(raw_reply)
            # Start the ramp
            cmd = 'SET:DEV:{}:PSU:ACTN:RTOS'.format(uid)
            raw_reply = self.instr.query(cmd)
            print(raw_reply)
        return setpoint

    def pressure_setpoint(self, uid: str, setpoint: float = None) -> float:
        if setpoint is None:
            # This code is almost identical to _read_value()....
            cmd = 'READ:DEV:{}:PRES:LOOP:PRST?'.format(uid)
            raw_reply = self.instr.query(cmd)
            print('Raw reply: ', raw_reply)
            fields = raw_reply.split(':')
            value_raw = fields[-1]
            for i in range(1, len(value_raw)):
                try:
                    actual_setpoint = float(value_raw[0 : i + 1])
                except ValueError:
                    break
            return actual_setpoint

        # If we are here, we are setting a setpoint
        if setpoint < 0:
            setpoint = 0
        if setpoint > 20:
            setpoint = 20

        print('Set setpoint to {}mBar'.format(setpoint))
        cmd = 'SET:DEV:{}:PRES:LOOP:PRST:{}mB'.format(uid, setpoint)
        raw_reply = self.instr.query(cmd)
        print(raw_reply)
        cmd = 'SET:DEV:{}:PRES:LOOP:ENAB:ON'.format(uid)
        raw_reply = self.instr.query(cmd)
        print(raw_reply)
        return setpoint


if __name__ == '__main__':
    itc = OxfordMercury(hostname='192.168.0.20')

    # print('ITC config:', itc.read_configuration().split('DEV'))
    # print('VTI Temp: ', itc.read_temperature('MB1.T1'))
    # print('VTI Temp: ', itc.read_temperature_details('MB1.T1'))
    # print('Probe temp: ', itc.read_temperature('DB8.T1'))

    # itc.temperature_setpoint('MB1.T1', 5)

    print()
    # THIS IS THE STEPPER MOTOR
    cmd = 'READ:DEV:DB4.G1:AUX?'
    print(itc.instr.query(cmd))
    # print(itc.read_needle_valve('DB4.G1:AUX:'))

    # THE SETPOINT IS CONTROLLED VIA THE PRESSURE UID

    print()

    # [':DB4.G1:AUX:']
    print('VTI Pressure: ', itc.read_pressure('DB5.P1'))
    # print('Probe heater: ', itc.read_heater('DB3.H1'))
    print('VTI heater: ', itc.read_heater('MB0.H1'))

    print(itc.pressure_setpoint('DB5.P1', 6))

    exit()
    print()
    ips = OxfordMercury(hostname='192.168.0.21')
    # print(ips.read_configuration().split('DEV'))
    print('Magnet: ', ips.read_temperature('MB1.T1'))  # Magnet
    print('PT2: ', ips.read_temperature('DB7.T1'))  # PT2
    print('PT1: ', ips.read_temperature('DB8.T1'))  # PT1

    print(ips.read_magnet_details('PSU.M1'))  # These are the two power supplies
    # print(ips.read_magnet_details('PSU.M2')) # They show the same values
    print(ips.read_magnet_details('GRPZ'))  # This is quite likely a better choice

    print(ips.read_magnetic_field('PSU.M1'))
    print(ips.read_magnetic_field('PSU.M2'))
    print(ips.read_magnetic_field('GRPZ'))
    print(ips.read_magnetic_field('GRPX'))  # No XY magnet installed
    print(ips.read_magnetic_field('GRPY'))  # No XY magnet installed

    print(ips.read_magnetic_field('GRPS'))  # No idea what this is
    exit()

    # print(itc.read_software_version())
    # print(itc.read_heater('DB1.H1'))

    uid = 'DB11'
    cmd = 'READ:DEV:{}'.format(uid)
    # cmd = 'READ:DEV:{}:HTR:VLIM'.format(uid)
    # cmd = 'READ:DEV:{}:HTR:SIG:POWR?'.format(uid)
    # STAT:DEV:DB1.H1:HTR:SIG:POWR:0.0000W
    # cmd = 'READ:DEV:{}:HTR:SIG:POWR?'.format(uid)
    # STAT:DEV:DB1.H1:HTR:SIG:POWR:18.4934W
    print(cmd)
    raw_reply = itc.scpi_comm(cmd, expect_return=True)
    print(raw_reply)

    exit()
    ips = OxfordMercury(hostname='192.168.0.21')

    print(ips.read_software_version())
    print(itc.read_software_version())

    print(itc.read_heater('DB1.H1'))

    print()
    # VTI_TEMP_DB6.H1
    # uid = 'DB1.H1'

    uid = 'DB1.H1'
    cmd = 'READ:DEV:{}:HTR:PMAX'.format(uid)
    # cmd = 'READ:DEV:{}:HTR:VLIM'.format(uid)
    # cmd = 'READ:DEV:{}:HTR:SIG:POWR?'.format(uid)
    # STAT:DEV:DB1.H1:HTR:SIG:POWR:0.0000W
    cmd = 'READ:DEV:{}:HTR:SIG:POWR?'.format(uid)
    # STAT:DEV:DB1.H1:HTR:SIG:POWR:18.4934W

    ###cmd = 'SET:DEV:{}:PSU:SIG:FSET:{}T'.format(uid, setpoint)
    # cmd = 'SET:DEV:{}:HTR:SIG:FSET:0.1W'.format(uid)
    print(cmd)
    raw_reply = itc.scpi_comm(cmd, expect_return=True)
    print(raw_reply)

    exit()

    # print(mitc.b_field_setpoint(3))

    # cmd = 'SET:DEV:PSU.M1:PSU:SIG:RCST:2.5A/m'
    # ips.scpi_comm(cmd)
    cmd = 'READ:DEV:PSU.M1:PSU:SIG:RCST?'  # Current ramp rate
    raw_reply = ips.scpi_comm(cmd, expect_return=True)
    print(raw_reply)

    cmd = 'SET:DEV:GRPZ:PSU:SIG:RFST:0.25T/m'
    ips.scpi_comm(cmd)
    cmd = 'READ:DEV:GRPZ:PSU:SIG:RFST?'
    raw_reply = ips.scpi_comm(cmd, expect_return=True)
    print(raw_reply)

    # print(mitc.read_temperature('MB1.T1'))  # Sample temperature
    # print(mitc.read_temperature('DB6.T1'))  # VTI temperature
    # print(mitc.read_temperature('DB7.T1'))  # Magnet temperature
    # print(mitc.read_pressure('DB8.P1'))  # VTI pressure
    # print(mitc.read_heater('MB0.H1'))  # Sample heater
    # print(mitc.read_heater('DB1.H1'))  # VTI heater

    # print(mitc.sample_temperature('MB1.T1'))
    # mips = OxfordMercury('/dev/ttyACM1')
    # print(mips.read_magnetic_field('GRPZ'))

    # print(mips.read_software_version())
    # # print(mips.read_configuration())

    # print(mips.switch_heater_state('GRPZ'))
    # # print(mips.set_field_setpoint('GRPZ', 0.5))
    # print(mips.b_field_setpoint('GRPZ'))
    # print(mips.b_field_setpoint('GRPZ'))
    # print(mips.b_field_setpoint('PSU.M1'))

    # # print(mips.read_temperature('PSU.M1'))

    pass
