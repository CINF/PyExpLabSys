import minimalmodbus
import serial
from PyExpLabSys.common.supported_versions import python3_only

python3_only(__file__)
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
import math
import time
import threading
from Modbus_comm_commands import Motor
from datetime import datetime, timedelta
import json

# The read_parameter function calls functions from the Modbus_comm_commands for the x, y and z motor
def read_parameter(parameter):
    data = [0, 0, 0]
    data[0] = eval('motx.' + parameter + '()')
    data[1] = eval('moty.' + parameter + '()')
    data[2] = eval('motz.' + parameter + '()')
    return data


# The read_parameter_all function calls functions from the Modbus_comm_commands for the x, y, z and z2 motor
def read_parameter_all(parameter):
    data = [0, 0, 0, 0]
    data[0] = eval('motx.' + parameter + '()')
    data[1] = eval('moty.' + parameter + '()')
    data[2] = eval('motz.' + parameter + '()')
    data[3] = eval('motz2.' + parameter + '()')
    return data


# The motor_socket calss is a threaded class that runs the socket and receive and send data
class motor_socket(threading.Thread):
    def __init__(self, datasocket, pushsocket):
        threading.Thread.__init__(self)
        self.datasocket = datasocket
        self.pushsocket = pushsocket
        # Initialise checks that are used to stop and pause threaded processes
        self.quit = False
        self.pause = False

    # The run function is a threaded function that runs undtil closed by a keyboardinterrupt
    # Reads parameters from the motor drivers and send it to the data pull socket
    def run(self):
        command_check = 'none'
        alarm_checkx = 'none'
        alarm_checky = 'none'
        alarm_checkz = 'none'
        alarm_type = {
            '0': 'No alarm',
            '10': 'Excessive position deviation',
            '20': 'Overcurrent',
            '21': 'Main circuit overheat',
            '22': 'Overvoltage (AC/DC power input driver)',
            '23': 'Main power supply OFF',
            '25': 'Undervoltage',
            '26': 'Motor overheat',
            '28': 'Sensor error',
            '2A': 'ABZO sensor communication error',
            '30': 'Overload',
            '31': 'Overspeed',
            '33': 'Absolute position error',
            '34': 'Command pulse error',
            '41': 'EEPROM error',
            '42': 'Sensor error at power on',
            '43': 'Rotation error at power on',
            '44': 'Encoder EEPROM error',
            '45': 'Motor combination error',
            '4A': 'Return-to-home incomplete',
            '51': 'Regeneration unit overheat (only AC power input driver)',
            '53': 'Emergency stop circuit error',
            '60': '±LS both sides active',
            '61': 'Reverse ±LS connection',
            '62': 'Return-to-home operation error',
            '63': 'No HOMES',
            '64': 'TIM, Z, SLIT signal error',
            '66': 'Hardware overtravel',
            '67': 'Software overtravel',
            '68': 'Emergency stop',
            '6A': 'Return-to-home operation offset error',
            '6D': 'Mechanical overtravel',
            '70': 'Operation data error',
            '71': 'Electronic gear setting error',
            '72': 'Wrap setting error',
            '81': 'Network bus error',
            '83': 'Communication switch setting error',
            '84': 'RS-485 communication error',
            '85': 'RS-485 communication timeout',
            '8E': 'Network converter error',
            'F0': 'CPU error',
        }
        while not self.quit:
            while self.pause:
                time.sleep(0.1)
            self.command_position = read_parameter('get_command_position')
            self.datasocket.set_point('command_position', self.command_position)
            self.status = read_parameter_all('get_status')
            self.datasocket.set_point('status', self.status)
            self.home_end = read_parameter('get_home_end')
            self.datasocket.set_point('home_end', self.home_end)
            self.move = read_parameter('get_move')
            self.datasocket.set_point('move', self.move)
            self.operating_speed = read_parameter('get_operating_speed')
            self.alarm_status = read_parameter('get_alarm_status')
            if self.alarm_status[0] == 1:
                current_alarm = motx.get_alarm()
                if current_alarm != alarm_checkx:
                    alarm_checkx = current_alarm
                    message = 'Motor X alarm {}: {}'.format(
                        current_alarm, alarm_type[current_alarm]
                    )
                    datasocket.set_point_now('message', message)
            if self.alarm_status[1] == 1:
                current_alarm = moty.get_alarm()
                if current_alarm != alarm_checky:
                    alarm_checky = current_alarm
                    message = 'Motor Y alarm {}: {}'.format(
                        current_alarm, alarm_type[current_alarm]
                    )
                    datasocket.set_point_now('message', message)
            if self.alarm_status[2] == 1:
                current_alarm = motz.get_alarm()
                if current_alarm != alarm_checkz:
                    alarm_checkz = current_alarm
                    message = 'Motor Z alarm {}: {}'.format(
                        current_alarm, alarm_type[current_alarm]
                    )
                    datasocket.set_point_now('message', message)
            # Checks if there has been a new message sent from the GUI
            # If a new message is recieved it performes various commands
            # Some threaded functions can be executed and can only be stopped by calling the 'stop' command from the GUI
            try:
                new_update = self.pushsocket.last[1]['command']
                if new_update != command_check:
                    command_check = new_update
                    command = new_update[11:]
                    if command == 'stop':
                        self.thread_quit = True
                        motx.stop()
                        moty.stop()
                        motz.stop()
                        print('Stop button pressed')
                        datasocket.set_point_now('message', 'Stop button pressed')
                    if command == 'move_home':
                        self.thread_quit = False
                        thread = threading.Thread(target=move_home)
                        thread.start()
                    if command == 'move_ISS':
                        self.thread_quit = False
                        thread = threading.Thread(target=move_chamber, args=('ISS',))
                        thread.start()
                    if command == 'move_Mg_XPS':
                        self.thread_quit = False
                        thread = threading.Thread(target=move_chamber, args=('Mg_XPS',))
                        thread.start()
                    if command == 'move_Al_XPS':
                        self.thread_quit = False
                        thread = threading.Thread(target=move_chamber, args=('Al_XPS',))
                        thread.start()
                    if command == 'move_SIG':
                        self.thread_quit = False
                        thread = threading.Thread(target=move_chamber, args=('SIG',))
                        thread.start()
                    if command == 'move_Baking':
                        self.thread_quit = False
                        thread = threading.Thread(target=move_chamber, args=('Baking',))
                        thread.start()
                    if command[0:8] == 'relative':
                        self.thread_quit = True
                        if command[8] == 'X':
                            motx.set_position(float(command[9:]))
                            motx.set_operation_trigger(1)
                        if command[8] == 'Y':
                            moty.set_position(float(command[9:]))
                            moty.set_operation_trigger(1)
                        if command[8] == 'Z':
                            motz.set_position(float(command[9:]))
                            motz.set_operation_trigger(1)
                    if command[0:8] == 'absolute':
                        self.thread_quit = True
                        if command[8] == 'X':
                            command_position = self.command_position[0]
                            motx.set_position(
                                (float(command[9:]) * 100 - command_position * 100)
                                / 100
                            )
                            motx.set_operation_trigger(1)
                        if command[8] == 'Y':
                            command_position = self.command_position[1]
                            moty.set_position(
                                (float(command[9:]) * 100 - command_position * 100)
                                / 100
                            )
                            moty.set_operation_trigger(1)
                        if command[8] == 'Z':
                            command_position = self.command_position[2]
                            motz.set_position(
                                (float(command[9:]) * 100 - command_position * 100)
                                / 100
                            )
                            motz.set_operation_trigger(1)
                    if command[0:17] == 'show_alarm_record':
                        if command[17] == 'X':
                            alarm_record = motx.get_alarm_record()
                            alarm_record.append('X')
                            alarm_record.append('alarm_record')
                            datasocket.set_point_now('message', alarm_record)
                        if command[17] == 'Y':
                            alarm_record = moty.get_alarm_record()
                            alarm_record.append('Y')
                            alarm_record.append('alarm_record')
                            datasocket.set_point_now('message', alarm_record)
                        if command[17] == 'Z':
                            alarm_record = motz.get_alarm_record()
                            alarm_record.append('Z')
                            alarm_record.append('alarm_record')
                            datasocket.set_point_now('message', alarm_record)
                    if command[0:18] == 'clear_alarm_record':
                        if command[18] == 'X':
                            motx.clear_alarm_record()
                            datasocket.set_point_now(
                                'message', 'Motor X alarm record reset'
                            )
                        if command[18] == 'Y':
                            moty.clear_alarm_record()
                            datasocket.set_point_now(
                                'message', 'Motor Y alarm record reset'
                            )
                        if command[18] == 'Z':
                            motz.clear_alarm_record()
                            datasocket.set_point_now(
                                'message', 'Motor Z alarm record reset'
                            )
                    if command == 'reset_alarms':
                        motx.reset_alarm()
                        moty.reset_alarm()
                        motz.reset_alarm()
                        alarm_checkx = 'none'
                        alarm_checky = 'none'
                        alarm_checkz = 'none'
                        datasocket.set_point_now('message', 'Current alarms reset')
                    if command == 'clear_ETO':
                        motx.clear_ETO()
                        moty.clear_ETO()
                        motz.clear_ETO()
                        datasocket.set_point_now(
                            'message', 'External Torque Off mode cleared'
                        )
                    if command == 'table_update':
                        self.table_update()
                    if command[:10] == 'table_save':
                        data = self.pushsocket.last[1]
                        self.table_save(data)
            except (TypeError, KeyError):
                continue
        print('Socket closed')

    # The table_update function reads the parameter and location data of each driver and send it through the pull socket to the GUI
    # It also send a update_check message to tell the GUI that it has finished
    def table_update(self):
        parameterlist = [
            'operating_speed',
            'starting_speed',
            'starting_changing_rate',
            'stopping_deceleration',
            'operating_current',
            'positive_software_limit',
            'negative_software_limit',
            'electronic_gear_A',
            'electronic_gear_B',
            'zhome_operating_speed',
            'zhome_starting_speed',
            'zhome_acceleration_deceleration',
            'group_id',
        ]
        for i in parameterlist:
            self.datasocket.set_point(i, read_parameter_all('get_initial_' + i))

        parameterlist = ['ISS', 'Mg_XPS', 'Al_XPS', 'SIG', 'HPC', 'Baking']
        for i in parameterlist:
            self.datasocket.set_point(i, read_parameter('get_' + i + '_location'))
        self.datasocket.set_point_now('update_check', True)
        time.sleep(1.5)
        self.datasocket.set_point_now('update_check', False)

    # The table_save function saves the data received from to GUI onto each driver
    def table_save(self, data):
        data = json.loads(data)
        parameterlist = [
            'operating_speed',
            'starting_speed',
            'starting_changing_rate',
            'stopping_deceleration',
            'operating_current',
            'positive_software_limit',
            'negative_software_limit',
            'electronic_gear_A',
            'electronic_gear_B',
            'zhome_operating_speed',
            'zhome_starting_speed',
            'zhome_acceleration_deceleration',
            'group_id',
        ]
        for i in parameterlist:
            eval('motx.' + 'set_initial_' + i + '({})'.format(data[i][0]))
            eval('moty.' + 'set_initial_' + i + '({})'.format(data[i][1]))
            eval('motz.' + 'set_initial_' + i + '({})'.format(data[i][2]))
            eval('motz2.' + 'set_initial_' + i + '({})'.format(data[i][3]))

        parameterlist = ['ISS', 'Mg_XPS', 'Al_XPS', 'SIG', 'HPC', 'Baking']
        for i in parameterlist:
            self.datasocket.set_point(i, data[i])
            eval('motx.' + 'set_' + i + '_location({})'.format(data[i][0]))
            eval('moty.' + 'set_' + i + '_location({})'.format(data[i][1]))
            eval('motz.' + 'set_' + i + '_location({})'.format(data[i][2]))

        motx.save_RAM_to_non_volatile()
        moty.save_RAM_to_non_volatile()
        motz.save_RAM_to_non_volatile()
        motz2.save_RAM_to_non_volatile()
        motx.load_RAM_to_direct()
        moty.load_RAM_to_direct()
        motz.load_RAM_to_direct()
        motz2.load_RAM_to_direct()


# The move_home function moves each motor home
# If the x motor position is greater than 350 mm it produces an error
# The function sleeps in between movement and checks if a stop signal has been sent from the GUI
# The continues reading of parameter data is also stopped when commands are called
# This is done to prevent several command being sent to the drivers at the same time
# First the z motor is returned to home, then the y motor and lastly the x motor
def move_home():
    xcommand_position = motor_socket.command_position[0]
    ycommand_position = motor_socket.command_position[1]
    zcommand_position = motor_socket.command_position[2]
    xspeed = motor_socket.operating_speed[0] / 100
    yspeed = motor_socket.operating_speed[1] / 100
    zspeed = motor_socket.operating_speed[2] / 100
    if xcommand_position < 350:
        delay = (abs(zcommand_position) / zspeed) + 1
        motor_socket.pause = True
        time.sleep(1.5)
        motz.home()
        motor_socket.pause = False
        for i in range(math.ceil(delay) * 5):
            if motor_socket.thread_quit:
                return
            time.sleep(0.2)
        datasocket.set_point_now('message', 'Z home')

        delay = (abs(ycommand_position) / yspeed) + 1
        motor_socket.pause = True
        time.sleep(1.5)
        moty.home()
        motor_socket.pause = False
        for i in range(math.ceil(delay) * 5):
            if motor_socket.thread_quit:
                return
            time.sleep(0.2)
        datasocket.set_point_now('message', 'Y home')

        delay = (abs(xcommand_position) / xspeed) + 1
        motor_socket.pause = True
        time.sleep(1.5)
        motx.home()
        motor_socket.pause = False
        for i in range(math.ceil(delay) * 5):
            if motor_socket.thread_quit:
                return
            time.sleep(0.2)
        datasocket.set_point_now('message', 'X home')
    elif xcommand_position > 350:
        datasocket.set_point_now('message', 'Error: X position is greater than 350 mm')
        print('Error')


# The move_chamber function moves to a given location in the chamber
# If the x motor position is greater than 350 mm it produces an error
# First the z and y motor are returned to home. The x motor is then brought into position followed by the z motor and lastly the y motor
def move_chamber(location):
    xcommand_position = motor_socket.command_position[0]
    ycommand_position = motor_socket.command_position[1]
    zcommand_position = motor_socket.command_position[2]
    xspeed = motor_socket.operating_speed[0] / 100
    yspeed = motor_socket.operating_speed[1] / 100
    zspeed = motor_socket.operating_speed[2] / 100
    if xcommand_position < 350:
        delay = (abs(zcommand_position) / zspeed) + 1
        motor_socket.pause = True
        time.sleep(1.5)
        target = read_parameter('get_' + location + '_location')
        x_target = target[0]
        y_target = target[1]
        z_target = target[2]
        motz.home()
        motor_socket.pause = False
        for i in range(math.ceil(delay) * 5):
            if motor_socket.thread_quit:
                return
            time.sleep(0.2)
        datasocket.set_point_now('message', 'Z home')

        delay = (abs(ycommand_position) / yspeed) + 1
        motor_socket.pause = True
        time.sleep(1.5)
        moty.home()
        motor_socket.pause = False
        for i in range(math.ceil(delay) * 5):
            if motor_socket.thread_quit:
                return
            time.sleep(0.2)
        datasocket.set_point_now('message', 'Y home')

        motor_socket.pause = True
        time.sleep(1.5)
        motx.set_position((x_target * 100 - xcommand_position * 100) / 100)
        delay = (abs(x_target - xcommand_position) / xspeed) + 1
        motx.set_operation_trigger(1)
        motor_socket.pause = False
        for i in range(math.ceil(delay) * 5):
            if motor_socket.thread_quit:
                return
            time.sleep(0.2)
        datasocket.set_point_now('message', 'X in target position')

        motor_socket.pause = True
        time.sleep(1.5)
        motz.set_position(z_target)
        delay = (abs(z_target) / zspeed) + 1
        motz.set_operation_trigger(1)
        motor_socket.pause = False
        for i in range(math.ceil(delay) * 5):
            if motor_socket.thread_quit:
                return
            time.sleep(0.2)
        datasocket.set_point_now('message', 'Z in target position')

        motor_socket.pause = True
        time.sleep(1.5)
        moty.set_position(y_target)
        delay = (abs(y_target) / yspeed) + 1
        moty.set_operation_trigger(1)
        motor_socket.pause = False
        for i in range(math.ceil(delay) * 5):
            if motor_socket.thread_quit:
                return
            time.sleep(0.2)
        datasocket.set_point_now('message', 'Y in target position')

    elif xcommand_position > 350:
        datasocket.set_point_now('message', 'Error: X position is greater than 350 mm')
        print('Error')


# Run when the script is opened
# Checks the status of the motors and opens the push and pull socket
# When a keyboardinterrupt is produced it send a signal to close the threaded function updating the GUI before closing
if __name__ == '__main__':

    port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FT1EI9CY-if00-port0'

    motx = Motor(port, 1)
    moty = Motor(port, 2)
    motz = Motor(port, 3)
    motz2 = Motor(port, 4)

    status = [False, True]
    print('Mot X status: {}'.format(status[motx.get_status()]))
    print('Mot Y status: {}'.format(status[moty.get_status()]))
    print('Mot Z status: {}'.format(status[motz.get_status()]))
    print('Mot Z2 status: {}'.format(status[motz2.get_status()]))

    datasocketlist = [
        'command_position',
        'status',
        'target_position',
        'home_end',
        'move',
        'operating_speed',
        'starting_speed',
        'starting_changing_rate',
        'stopping_deceleration',
        'operating_current',
        'positive_software_limit',
        'negative_software_limit',
        'electronic_gear_A',
        'electronic_gear_B',
        'zhome_operating_speed',
        'zhome_starting_speed',
        'zhome_acceleration_deceleration',
        'group_id',
        'ISS',
        'Mg_XPS',
        'Al_XPS',
        'SIG',
        'HPC',
        'Baking',
        'message',
        'update_check',
    ]

    if (
        motx.get_status() == 1
        and moty.get_status() == 1
        and motz.get_status() == 1
        and motz2.get_status() == 1
    ):
        datasocket = DateDataPullSocket('motor_controller', datasocketlist, port=9000)
        datasocket.start()

        pushsocket = DataPushSocket('motor_push_control', action='store_last')
        pushsocket.start()

        motor_socket = motor_socket(datasocket, pushsocket)
        motor_socket.start()

        try:
            while not motor_socket.quit:
                time.sleep(1)
        except KeyboardInterrupt:
            print('Quitting')
            motor_socket.quit = True
            time.sleep(2)
            datasocket.stop()
            pushsocket.stop()
    else:
        print('No communication with the instrument')
