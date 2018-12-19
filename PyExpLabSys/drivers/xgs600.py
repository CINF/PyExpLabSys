"""Driver class for XGS600 gauge controll"""
from __future__ import print_function
import time
import serial
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)


class XGS600Driver():
    """Driver for XGS600 gauge controller"""
    def __init__(self, port='/dev/ttyUSB1', timeout=2.0):
        self.serial = serial.Serial(port)
        self.timeout = timeout

    def xgs_comm(self, command, expect_reply=True):
        """Implements basic communication"""
        # Write command
        self.serial.read(self.serial.inWaiting())  # Clear waiting characters
        comm = "#00" + command + "\r"  # #00 is RS232 communication and #aa is RS485
        self.serial.write(comm.encode('ascii'))

        # Read reply if requested
        # Expected reply is always '>'+reply+'\r'
        # A reply can either be hex value or string or list of strings
        t_start_reply = time.time()
        time.sleep(0.25)
        if expect_reply:
            gathered_reply = ''
            number_of_bytes = self.serial.inWaiting()
            gathered_reply += self.serial.read(number_of_bytes).decode()
            while not gathered_reply.endswith('\r'):
                print("Waiting for rest of reply, reply so far is: ", repr(gathered_reply))
                number_of_bytes = self.serial.inWaiting()
                gathered_reply += self.serial.read(number_of_bytes).decode()

                if time.time() - t_start_reply > self.timeout:
                    raise TimeoutError
                time.sleep(0.25)

            return gathered_reply.replace('>', '').replace('\r', '')

    def read_all_pressures(self):
        """Read pressure from all sensors"""
        pressures = [-3]
        error = 1
        while (error > 0) and (error < 10):
            pressure_string = self.xgs_comm("0F")
            if len(pressure_string) > 0:
                error = 0
                temp_pressure = pressure_string.replace(' ', '').split(',')
                pressures = []
                for press in temp_pressure:
                    if press == 'OPEN':
                        pressures.append('OPEN')
                    else:
                        try:
                            pressures.append((float)(press))
                        except ValueError:
                            pressures.append(-2)
            else:
                time.sleep(0.2)
                error = error +1
        return pressures


    def list_all_gauges(self):
        """List all installed gauge cards"""
        gauge_string = self.xgs_comm("01")
        gauges = ""
        for gauge_number in range(0, len(gauge_string), 2):
            gauge = gauge_string[gauge_number:gauge_number+2]
            if gauge == "10":
                gauges = gauges + str(gauge_number/2) + ": Hot Filament Gauge\n"
            if gauge == "FE":
                gauges = gauges + str(gauge_number/2) + ": Empty Slot\n"
            if gauge == "40":
                gauges = gauges + str(gauge_number/2) + ": Convection Board\n"
            if gauge == "3A":
                gauges = gauges + str(gauge_number/2) + ": Inverted Magnetron Board\n"
        return gauges

    def read_pressure(self, gauge_id):
        """Read the pressure from a specific gauge.
        gauge_id is represented as Uxxxxx and xxxxx is the userlabel"""
        pressure = self.xgs_comm('02' + gauge_id)
        try:
            val = float(pressure)
        except ValueError:
            val = -1.0
        return val

    def filament_lit(self, gauge_id):
        """Report if the filament of a given gauge is lid"""
        filament = self.xgs_comm('34' + gauge_id)
        return int(filament)

    def emission_status(self, gauge_id):
        """Read the status of the emission for a given gauge"""
        status = self.xgs_comm('32' + gauge_id)
        emission = status == '01'
        return emission

    def set_smission_off(self, gauge_id):
        """Turn off emission from a given gauge"""
        self.xgs_comm('30' + gauge_id, expect_reply=False)
        time.sleep(0.1)
        return self.emission_status(gauge_id)

    def set_emission_on(self, gauge_id, filament):
        """Turn on emission for  a given gauge"""
        if filament == 1:
            command = '31'
        if filament == 2:
            command = '33'
        self.xgs_comm(command + gauge_id, expect_reply=False)
        return self.emission_status(gauge_id)

    def read_software_version(self):
        """Read gauge controller firmware version"""
        gauge_string = self.xgs_comm("05")
        return gauge_string

    def read_pressure_unit(self):
        """Read which pressure unit is used"""
        gauge_string = self.xgs_comm("13")
        unit = gauge_string.replace(' ', '')
        if unit == "00":
            unit = "Torr"
        if unit == "01":
            unit = "mBar"
        if unit == "02":
            unit = "Pascal"
        return unit

    def read_setpoint_state(self):
        """
        Read all setpoint states as a hex value.
        Example 0005 corrosponds to state [T,F,T,F,F,F,F,F],
        and 0002 corrosponds to [F,T,F,F,F,F,F,F]
        """
        setpoint_state_string = self.xgs_comm("03")
        setpoint_state = setpoint_state_string.replace(' ', '')
        hex_to_binary = format(int(setpoint_state, base=16), '0>8b')  # format hex value to binari with 8bit
        binary_to_bool_list = [char == '1' for char in hex_to_binary]  # make binary number to boolean array
        states = list(reversed(binary_to_bool_list))  # Reverse boolean array to read states of valves left to right

        return states

    def read_setpoint(self, channel):
        """Read the Setpoint OFF/ON/AUTO for channel h in [1-8]"""
        setpoint_string = self.xgs_comm("5F"+str(channel))
        setpoint = setpoint_string.replace(' ', '')
        if str(setpoint) == "0":
            status = 'OFF'
        elif str(setpoint) == "3":
            status = 'AUTO'
        elif str(setpoint) == "1":
            status = 'ON'
        else:
            status = None
        return status

    def set_setpoint(self, channel, state):
        """"Set Setpoint OFF/ON/AUTO
        Example: #005E83 sets setpoint #8 to Auto
        """
        if state in [0, 1, 3]:
            state_reply = state
        elif state in ['0', '1', '3']:
            state_reply = int(state)
        elif state.lower() == 'auto':
            state_reply = 3
        elif state.lower() == 'off':
            state_reply = 0
        elif state.lower() == 'on':
            state_reply = 1
        else:
            return 'only (0,1,3) / ("OFF", "ON", "AUTO") is accepted'
        self.xgs_comm("5E"+str(channel)+str(state_reply), expect_reply=False)

    def set_setpoint_on(self, setpoint, sensor_code, sensor_count, pressure_on):
        """This sets the pressure setpoint of the valve where it will be on.
        hcnx.xxxE-xx, where h is setpoint 1-8, c is sensorcode, T for CNV and
        I for ion gauge, n is sensor count, press is pressure represented with x.xxxE-xx
        c could be U and and then n would be the user label"""
        if sensor_code == 'user_label':
            sensor_code = 'U'
        self.xgs_comm("6"+str(setpoint)+str(sensor_code)+str(sensor_count)+str(pressure_on),
                      expect_reply=False)
        print('On_string: ', "6"+str(setpoint)+str(sensor_code)+str(sensor_count)+str(pressure_on))

    def set_setpoint_off(self, setpoint, sensor_code, sensor_count, pressure_off):
        """This sets the pressure setpoint of the valve where it will be off.
        hcnx.xxxE-xx, where h is setpoint 1-8, c is sensorcode, T for CNV and
        I for ion gauge, U is user label, n is sensor count or the specific user label,
        press is pressure represented as x.xxxE-xx"""
        if sensor_code == 'user_label':
            sensor_code = 'U'
        self.xgs_comm("7"+str(setpoint)+str(sensor_code)+str(sensor_count)+str(pressure_off),
                      expect_reply=False)
        print('Off_string: ',
              "7"+str(sensor_code)+str(sensor_count)+str(sensor_count)+str(pressure_off))

    def read_all_user_label(self):
        """Read all user defined labels for gauge id Command Entry T for TC/CNV,
        I for ion gauge (HFIG or IMG) n Sensor Count
        Counting TCs or ion gauges from left to right from the front panel view."""
        user_labels = {}
        for i in range(1, 9):
            thermo_couple_string = self.xgs_comm("T"+str(i))
            ion_gauges_string = self.xgs_comm("I"+str(i))
            thermo_couple = thermo_couple_string.replace(' ', '')
            ion_gauges = ion_gauges_string.replace(' ', '')
            if thermo_couple != "?FF":
                user_labels['T'+str(i)] = thermo_couple
            else:
                pass
            if ion_gauges != "?FF":
                user_labels['I'+str(i)] = ion_gauges
            else:
                pass

        return user_labels


if __name__ == '__main__':
    XGS = XGS600Driver()
    print(XGS.read_all_pressures())
