"""
Self contained module to run a Pfeiffer turbo pump including fall-back
text gui and data logging.
"""
import time
import curses
import threading
import logging
import serial
from PyExpLabSys.common.supported_versions import python2_and_3
# Configure logger as library logger and set supported python versions
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
python2_and_3(__file__)

class CursesTui(threading.Thread):
    """ Text gui for controlling the pump """

    def __init__(self, turbo_instance):
        # TODO: Add support for several pumps in one gui
        threading.Thread.__init__(self)

        self.quit = False
        self.turbo = turbo_instance
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.screen.keypad(1)
        self.screen.nodelay(1)

    def run(self):
        while not self.quit:
            self.screen.addstr(3, 2, 'Turbo controller running')
            #if self.turbo.status['pump_accelerating']:
            self.screen.addstr(3, 41, '| Vent mode: ' \
                               + self.turbo.status['vent_mode'] + '      ')
            #    self.screen.clrtoeol()
            #else:
            #    self.screen.addstr(3, 30, 'Pump at constant speed')

            self.screen.addstr(4, 2, 'Gas mode: ' + self.turbo.status['gas_mode'] + '      ')
            tmp = '| Venting setpoint: {:d}%      '
            self.screen.addstr(4, 41, tmp.format(self.turbo.status['vent_freq']))
            self.screen.addstr(5, 2, 'Acc A1: ' + self.turbo.status['A1'] + '     ')
            tmp = '| Venting time: {0:.2f} minutes      '
            self.screen.addstr(5, 41, tmp.format(self.turbo.status['vent_time']))
            self.screen.addstr(6, 2, 'Sealing gas: ' +
                               self.turbo.status['sealing_gas'] + '      ')

            tmp = "Rotation speed: {0:.2f}Hz      "
            self.screen.addstr(8, 2, tmp.format(self.turbo.status['rotation_speed']))
            tmp = "Setpoint speed: {0:.2f}Hz      "
            self.screen.addstr(8, 28, tmp.format(self.turbo.status['set_rotation_speed']))
            tmp = "Drive current: {0:.2f}A        "
            self.screen.addstr(9, 2, tmp.format(self.turbo.status['drive_current']))
            tmp = "Drive power: {0:.0f}W          "
            self.screen.addstr(10, 2, tmp.format(self.turbo.status['drive_power']))

            tmp = "Temperature, Electronics: {0:.0f}C      "
            self.screen.addstr(12, 2, tmp.format(self.turbo.status['temp_electronics']))
            tmp = "Temperature, Bottom: {0:.0f}C           "
            self.screen.addstr(13, 2, tmp.format(self.turbo.status['temp_bottom']))
            tmp = "Temperature, Bearings: {0:.0f}C         "
            self.screen.addstr(14, 2, tmp.format(self.turbo.status['temp_bearings']))
            tmp = "Temperature, Motor: {0:.0f}C            "
            self.screen.addstr(15, 2, tmp.format(self.turbo.status['temp_motor']))

            tmp = "Operating hours: {0:.0f} ({1:.1f}days)    "
            hours = self.turbo.status['operating_hours']
            self.screen.addstr(18, 2, tmp.format(hours, hours / 24.0))
            tmp = "Driver runtime: {0:.1f}s    "
            self.screen.addstr(19, 2, tmp.format(self.turbo.status['runtime']))
            self.screen.addstr(20, 2, 'Port: ' + self.turbo.serial.port)
            self.screen.addstr(21, 2, 'q: quit, u: spin up, d: spin down')

            char_num = self.screen.getch()
            if char_num == ord('q'):
                self.turbo.running = False
                self.quit = True
                self.screen.addstr(2, 2, 'Quitting...')
            if char_num == ord('d'):
                self.turbo.status['spin_down'] = True
            if char_num == ord('u'):
                self.turbo.status['spin_up'] = True
            self.screen.refresh()
            time.sleep(0.2)

        LOGGER.info('TUI ended')

    def stop(self):
        """ Cleanup terminal """
        curses.nocbreak()
        self.screen.keypad(False)
        curses.echo()
        curses.endwin()

class TurboReader(threading.Thread):
    """ Keeps track of all data from a turbo pump with the intend of logging them """
    def __init__(self, turbo_instance):
        #TODO: Add support for several pumps
        threading.Thread.__init__(self)
        self.mal = 20  # Moving average length
        self.turbo = turbo_instance
        self.log = {}
        self.log['rotation_speed'] = {}
        self.log['rotation_speed']['time'] = 600
        self.log['rotation_speed']['change'] = 1.03
        self.log['rotation_speed']['mean'] = [0] * self.mal
        self.log['rotation_speed']['last_recorded_value'] = 0
        self.log['rotation_speed']['last_recorded_time'] = 0

        self.log['drive_current'] = {}
        self.log['drive_current']['time'] = 600
        self.log['drive_current']['change'] = 1.05
        self.log['drive_current']['mean'] = [0] * self.mal
        self.log['drive_current']['last_recorded_value'] = 0
        self.log['drive_current']['last_recorded_time'] = 0

        self.log['drive_power'] = {}
        self.log['drive_power']['time'] = 600
        self.log['drive_power']['change'] = 1.05
        self.log['drive_power']['mean'] = [0] * self.mal
        self.log['drive_power']['last_recorded_value'] = 0
        self.log['drive_power']['last_recorded_time'] = 0

        self.log['temp_motor'] = {}
        self.log['temp_motor']['time'] = 600
        self.log['temp_motor']['change'] = 1.05
        self.log['temp_motor']['mean'] = [0] * self.mal
        self.log['temp_motor']['last_recorded_value'] = 0
        self.log['temp_motor']['last_recorded_time'] = 0

        self.log['temp_electronics'] = {}
        self.log['temp_electronics']['time'] = 600
        self.log['temp_electronics']['change'] = 1.05
        self.log['temp_electronics']['mean'] = [0] * self.mal
        self.log['temp_electronics']['last_recorded_value'] = 0
        self.log['temp_electronics']['last_recorded_time'] = 0

        self.log['temp_bottom'] = {}
        self.log['temp_bottom']['time'] = 600
        self.log['temp_bottom']['change'] = 1.05
        self.log['temp_bottom']['mean'] = [0] * self.mal
        self.log['temp_bottom']['last_recorded_value'] = 0
        self.log['temp_bottom']['last_recorded_time'] = 0

        self.log['temp_bearings'] = {}
        self.log['temp_bearings']['time'] = 600
        self.log['temp_bearings']['change'] = 1.05
        self.log['temp_bearings']['mean'] = [0] * self.mal
        self.log['temp_bearings']['last_recorded_value'] = 0
        self.log['temp_bearings']['last_recorded_time'] = 0

    def run(self):
        for i in range(0, self.mal):
            time.sleep(0.5)
            for param in self.log:
                self.log[param]['mean'][i] = self.turbo.status[param]

        #Mean values now populated with meaningfull data
        while True:
            for i in range(0, self.mal):
                time.sleep(0.5)
                for param in self.log:
                    log = self.log[param]
                    log['mean'][i] = self.turbo.status[param]

class TurboLogger(threading.Thread):
    """ Read a specific value and determine whether it should be logged """
    def __init__(self, turboreader, parameter, maximumtime=600):
        threading.Thread.__init__(self)
        self.turboreader = turboreader
        self.parameter = parameter
        self.value = None
        self.maximumtime = maximumtime
        self.quit = False
        self.last_recorded_time = 0
        self.last_recorded_value = 0
        self.trigged = False

    def read_value(self):
        """ Read the value of the logger """
        return self.value

    def run(self):
        while not self.quit:
            time.sleep(2.5)
            log = self.turboreader.log[self.parameter]
            mean = sum(log['mean']) / float(len(log['mean']))
            self.value = mean
            time_trigged = (time.time() - self.last_recorded_time) > self.maximumtime
            val_trigged = not (self.last_recorded_value * 0.9 < self.value <
                               self.last_recorded_value * 1.1)
            if (time_trigged or val_trigged):
                self.trigged = True
                self.last_recorded_time = time.time()
                self.last_recorded_value = self.value


class TurboDriver(threading.Thread):
    """ The actual driver that will communicate with the pump """

    def __init__(self, adress=1, port='/dev/ttyUSB0'):
        threading.Thread.__init__(self)

        with open('turbo.txt', 'w'):
            pass
        logging.basicConfig(filename="turbo.txt", level=logging.INFO)
        logging.info('Program started.')
        logging.basicConfig(level=logging.INFO)

        self.serial = serial.Serial(port, 9600)
        self.serial.stopbits = 2
        self.serial.timeout = 0.1
        self.adress = adress
        self.status = {}  # Hold parameters to be accessible by gui
        self.status['starttime'] = time.time()
        self.status['runtime'] = 0
        self.status['rotation_speed'] = 0
        self.status['set_rotation_speed'] = 0
        self.status['operating_hours'] = 0
        self.status['pump_accelerating'] = False
        self.status['gas_mode'] = ''
        self.status['vent_mode'] = ''
        self.status['A1'] = ''
        self.status['vent_freq'] = 50
        self.status['vent_time'] = 0
        self.status['sealing_gas'] = ''
        self.status['drive_current'] = 0
        self.status['drive_power'] = 0
        self.status['temp_electronics'] = 0
        self.status['temp_bottom'] = 0
        self.status['temp_bearings'] = 0
        self.status['temp_motor'] = 0
        self.status['spin_down'] = False
        self.status['spin_up'] = False
        self.running = True

    def comm(self, command, read=True):
        """ Implementaion of the communication protocol with the pump.
        The function deals with common syntax need for all commands.

        :param command: The command to send to the pump
        :type command: str
        :param read: If True, read only not action performed
        :type read: Boolean
        :return: The reply from the pump
        :rtype: Str
        """
        adress_string = str(self.adress).zfill(3)

        if read:
            action = '00'
            datatype = '=?'
            length = str(len(datatype)).zfill(2)
            command = action + command + length + datatype
        crc = self.crc_calc(adress_string + command)
        command = adress_string + command + crc + '\r'
        LOGGER.debug(command)
        self.serial.write(command.encode('ascii'))
        response = self.serial.readline()
        try:
            length = int(response[8:10])
            reply = response[10:10 + length]
            crc = response[10 + length:10 + length + 3]
        except ValueError:
            logging.warn('Value error, unreadable reply')
            reply = -1
        # TODO: Implement real crc check
        except serial.SerialException:
            logging.warn('Serial connection problem')
            reply = -1
        return reply
    
    def crc_calc(self, command):
        """ Helper function to calculate crc for commands
        :param command: The command for which to calculate crc
        :type command: str
        :return: The crc value
        :rtype: Str
        """
        crc = 0
        for character in command:
            crc += ord(character)
        crc = crc % 256
        crc_string = str(crc).zfill(3)
        return crc_string

    def read_rotation_speed(self):
        """ Read the rotational speed of the pump

        :return: The rotaional speed in Hz
        :rtype: Float
        """
        command = '398'
        reply = self.comm(command, True)
        val = int(reply) / 60.0
        return val

    def read_set_rotation_speed(self):
        """ Read the intended rotational speed of the pump

        :return: The intended rotaional speed in Hz
        :rtype: Int
        """
        command = '308'
        reply = self.comm(command, True)
        val = int(reply)
        return val

    def read_operating_hours(self):
        """ Read the number of operating hours

        :return: Number of operating hours
        :rtype: Int
        """
        command = '311'
        reply = self.comm(command, True)
        val = int(reply)
        return val

    def read_gas_mode(self):
        """ Read the gas mode
        :return: The gas mode
        :rtype: Str
        """
        command = '027'
        reply = self.comm(command, True)
        mode = int(reply)
        mode_string = ''
        if mode == 0:
            mode_string = 'Heavy gasses'
        if mode == 1:
            mode_string = 'Light gasses'
        if mode == 2:
            mode_string = 'Helium'
        return mode_string

    def read_vent_mode(self):
        """ Read the venting mode
        :return: The venting mode
        :rtype: Str
        """
        command = '030'
        reply = self.comm(command, True)
        mode = int(reply)
        mode_string = ''
        if mode == 0:
            mode_string = 'Delayed Venting'
        if mode == 1:
            mode_string = 'No Venting'
        if mode == 2:
            mode_string = 'Direct Venting'
        return mode_string
    
    def read_vent_rotation(self):
        """ Adjust the rotation speed below which
        the turbo starts venting
        """
        command = '720'
        reply = self.comm(command, True)
        val = int(reply)
        return val

    def read_vent_time(self):
        """ Read the time the venting valve is kept open
        """
        command = '721'
        reply = self.comm(command, True)
        val = int(reply)/60.0
        return val
    
    def read_acc_a1(self):
        """ Read the status of accessory A1
        """
        command = '035'
        reply = self.comm(command, True)
        mode = int(reply)
        mode_string = ''
        if mode == 0:
            mode_string = "Fan (continous)"
        elif mode == 1:
            mode_string = "Venting valve, normally closed"
        elif mode == 4:
            mode_string = "Fan (temp controlled)"
        else:
            mode_string = "Mode is: " + str(mode)
        return mode_string
    
    def read_sealing_gas(self):
        """ Read whether sealing gas is applied
        :return: The sealing gas mode
        :rtype: Str
        """
        command = '050'
        reply = self.comm(command, True)
        mode = int(reply)
        mode_string = ''
        if mode == 0:
            mode_string = 'No sealing gas'
        if mode == 1:
            mode_string = 'Sealing gas on'
        return mode_string

    def is_pump_accelerating(self):
        """ Read if pump is accelerating
        :return: True if pump is accelerating, false if not
        :rtype: Boolean
        """
        command = '307'
        reply = self.comm(command, True)
        return int(reply) == 1

    def turn_pump_on(self, off=False):
        """ Spin the pump up or down
        :param off: If True the pump will spin down
        :type off: Boolean
        :return: Always returns True
        :rtype: Boolean
        """
        if not off:
            command = '1001006111111'
        else:
            command = '1001006000000'
        self.comm(command, False)
        return True

    def read_temperature(self):
        """ Read the various measured temperatures of the pump
        :return: Dictionary with temperatures
        :rtype: Dict
        """

        command = '326'
        reply = self.comm(command, True)
        elec = int(reply)

        command = '330'
        reply = self.comm(command, True)
        bottom = int(reply)

        command = '342'
        reply = self.comm(command, True)
        bearings = int(reply)

        command = '346'
        reply = self.comm(command, True)
        motor = int(reply)

        return_val = {}
        return_val['elec'] = elec
        return_val['bottom'] = bottom
        return_val['bearings'] = bearings
        return_val['motor'] = motor
        return return_val

    def read_drive_power(self):
        """ Read the current power consumption of the pump
        :return: Dictionary containing voltage, current and power
        :rtype: Dict
        """

        command = '310'
        reply = self.comm(command, True)
        current = int(reply)/100.0

        command = '313'
        reply = self.comm(command, True)
        voltage = int(reply)/100.0

        command = '316'
        reply = self.comm(command, True)
        power = int(reply)

        return_val = {}
        return_val['voltage'] = voltage
        return_val['current'] = current
        return_val['power'] = power
        return return_val

    def run(self):
        round_robin_counter = 0
        while self.running:
            #time.sleep(0.1)
            self.status['runtime'] = time.time() - self.status['starttime']
            self.status['rotation_speed'] = self.read_rotation_speed()

            power = self.read_drive_power()
            self.status['drive_current'] = power['current']
            self.status['drive_power'] = power['power']

            if round_robin_counter == 0:
                temp = self.read_temperature()
                self.status['temp_electronics'] = temp['elec']
                self.status['temp_bottom'] = temp['bottom']
                self.status['temp_bearings'] = temp['bearings']
                self.status['temp_motor'] = temp['motor']
            if round_robin_counter == 1:
                self.status['pump_accelerating'] = self.is_pump_accelerating()
                self.status['set_rotation_speed'] = self.read_set_rotation_speed()
                self.status['gas_mode'] = self.read_gas_mode()
                self.status['vent_mode'] = self.read_vent_mode()
                self.status['A1'] = self.read_acc_a1()
                self.status['vent_freq'] = self.read_vent_rotation()
                self.status['vent_time'] = self.read_vent_time()
                self.status['sealing_gas'] = self.read_sealing_gas()
                self.status['operating_hours'] = self.read_operating_hours()
            round_robin_counter += 1
            round_robin_counter = round_robin_counter % 2

            if self.status['spin_up']:
                self.turn_pump_on()
                self.status['spin_up'] = False
            if self.status['spin_down']:
                self.turn_pump_on(off=True)
                self.status['spin_down'] = False


if __name__ == '__main__':

    # Initialize communication with the turbo
    TURBO = TurboDriver()
    TURBO.start()

    # Start the user interface
    TUI = CursesTui(TURBO)
    TUI.start()
    try:
        while not TUI.quit:
            time.sleep(1)
    except KeyboardInterrupt:
        LOGGER.info("Program interrupted by user")
    finally:
        TUI.stop()
