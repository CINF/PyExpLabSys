# pylint: disable=C0103,R0904

"""
Self contained module to run a Pfeiffer turbo pump including fall-back
text gui and data logging.
"""

import serial
import time
import curses
import threading
import logging
import MySQLdb
from datetime import datetime

import sys
sys.path.append('/home/pi/PyExpLabSys/')
import FindSerialPorts

class CursesTui(threading.Thread):
    """ Text gui for controlling the pump """

    def __init__(self, turbo_instance):
        #TODO: Add support for several pumps in one gui
        threading.Thread.__init__(self)
        self.turbo = turbo_instance
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.screen.keypad(1)
        self.screen.nodelay(1)

    def run(self):
        while True:
            self.screen.addstr(3, 2, 'Turbo controller running')
            #if self.turbo.status['pump_accelerating']:
            #    self.screen.addstr(3, 30, 'Pump accelerating')
            #    self.screen.clrtoeol()
            #else:
            #    self.screen.addstr(3, 30, 'Pump at constant speed')
            self.screen.addstr(4, 2, 'Gas mode: ' + self.turbo.status['gas_mode'] + '      ')

            self.screen.addstr(6, 2, "Rotation speed: {0:.2f}Hz      ".format(self.turbo.status['rotation_speed']))
            self.screen.addstr(7, 2, "Drive current: {0:.2f}A        ".format(self.turbo.status['drive_current']))
            self.screen.addstr(8, 2, "Drive power: {0:.0f}W          ".format(self.turbo.status['drive_power']))

            self.screen.addstr(10, 2, "Temperature, Electronics: {0:.0f}C      ".format(self.turbo.status['temp_electronics']))
            self.screen.addstr(11, 2, "Temperature, Bottom: {0:.0f}C           ".format(self.turbo.status['temp_bottom']))
            self.screen.addstr(12, 2, "Temperature, Bearings: {0:.0f}C         ".format(self.turbo.status['temp_bearings']))
            self.screen.addstr(13, 2, "Temperature, Motor: {0:.0f}C            ".format(self.turbo.status['temp_motor']))

            self.screen.addstr(15,2, 'q: quit, u: spin up, d: spin down')

            n = self.screen.getch()
            if n == ord('q'):
                self.turbo.running = False
            if n == ord('d'):
                self.turbo.status['spin_down'] = True
            if n == ord('u'):
                self.turbo.status['spin_up'] = True

            self.screen.refresh()
            time.sleep(0.2)

    def stop(self):
        """ Cleanup terminal """
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()


class DataLogger(threading.Thread):
    """ Datalogging for turbo controller """
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

    def sqlInsert(self, query):
        """ Helper function to insert data into database """
        try:
            cnxn = MySQLdb.connect(host="servcinf", user="mgw", passwd="mgw", db="cinfdata")
            cursor = cnxn.cursor()
        except:
            print "Unable to connect to database"
            return()
        try:
            cursor.execute(query)
            cnxn.commit()
        except:
            print "SQL-error, query written below:"
            print query
            cnxn.close()


    def sqlTime(self):
        sqltime = datetime.now().isoformat(' ')[0:19]
        return(sqltime)

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
                    p = self.log[param]
                    p['mean'][i] = self.turbo.status[param]
                    mean = sum(p['mean']) / float(len(p['mean']))
                    time_trigged = (time.time() - p['last_recorded_time']) > p['time']
                    val_trigged = not (p['last_recorded_value'] * p['change'] < mean < p['last_recorded_value'] * p['change'])

                    if (time_trigged or val_trigged):
                        p['last_recorded_value'] = mean
                        p['last_recorded_time'] = time.time()
                        meas_time = self.sqlTime()
                        sql = "insert into dateplots_mgw set type=\"" + param + "\", time=\"" +  meas_time + "\", value = " + str(mean)
                        #print sql
                        self.sqlInsert(sql)


class TurboDriver(threading.Thread):
    """ The actual driver that will communicate with the pump """

    def __init__(self, adress=1, port='/dev/ttyUSB3'):
        threading.Thread.__init__(self)

        with open('turbo.txt', 'w'):
            pass
        logging.basicConfig(filename="turbo.txt", level=logging.INFO)
        logging.info('Program started.')
        logging.basicConfig(level=logging.INFO)

        self.f = serial.Serial(port, 9600)
        self.f.stopbits = 2
        self.f.timeout = 0.1
        self.adress = adress
        self.status = {}  # Hold parameters to be accessible by gui
        self.status['rotation_speed'] = 0
        self.status['pump_accelerating'] = False
        self.status['gas_mode'] = ''
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
        self.f.write(adress_string + command + crc + '\r')
        a = ''
        response = ''
        while not (a == '\r'):
            a = self.f.read()
            if len(a)==0:
                raise(IOError('Communication Error'))
            response += a
        length = int(response[8:10])
        reply = response[10:10+length]
        crc = response[10+length:10+length+3]
        if crc:
            return reply
        else:
            return 'Error!'

    def crc_calc(self, command):
        """ Helper function to calculate crc for commands
        :param command: The command for which to calculate crc
        :type command: str
        :return: The crc value
        :rtype: Str
        """
        crc = 0
        for s in command:
            crc += ord(s)
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
        val = int(reply)/60.0
        #logging.warn(val)
        #command = '309'
        #reply = self.comm(command, True)
        #logging.warn(reply)
        return(val)

    def read_gas_mode(self):
        """ Read the gas mode
        :return: The gas mode
        :rtype: Str
        """

        command = '027'
        reply = self.comm(command, True)
        mode = int(reply)
        if mode == 0:
            return 'Heavy gasses'
        if mode == 1:
            return 'Light gasses'
        if mode == 2:
            return 'Helium'

    def is_pump_accelerating(self):
        """ Read if pump is accelerating
        :return: True if pump is accelerating, false if not
        :rtype: Boolean
        """
        command = '307'
        reply = self.comm(command, True)
        if int(reply) == 1:
            return(True)
        else:
            return(False)

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
        return(True)

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
        while self.running:
            time.sleep(0.1)
            self.status['pump_accelerating'] = self.is_pump_accelerating()
            self.status['rotation_speed'] = self.read_rotation_speed()
            self.status['gas_mode'] = self.read_gas_mode()

            power = self.read_drive_power()
            self.status['drive_current'] = power['current']
            self.status['drive_power'] = power['power']

            temp = self.read_temperature()
            self.status['temp_electronics'] = temp['elec']
            self.status['temp_bottom'] = temp['bottom']
            self.status['temp_bearings'] = temp['bearings']
            self.status['temp_motor'] = temp['motor']

            if self.status['spin_up']:
                self.turn_pump_on()
                self.status['spin_up'] = False
            if self.status['spin_down']:
                self.turn_pump_on(off=True)
                self.status['spin_down'] = False


if __name__ == '__main__':
    ports = FindSerialPorts.find_ports()
    for port in ports:
        mainpump = TurboDriver(adress=2,port='/dev/' + port)
        try:
            mainpump.read_rotation_speed()
            break
        except IOError:
            pass
    print 'Serial port: ' + port
    mainpump.start()

    tui = CursesTui(mainpump)
    tui.daemon = True
    tui.start()

    #logger = DataLogger(mainpump)
    #logger.daemon = True
    #logger.start()
