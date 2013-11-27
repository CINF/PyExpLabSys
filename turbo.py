import serial
import time
import curses
import threading
import logging

class CursesTui(threading.Thread):
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
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()    


class TurboDriver(threading.Thread):
    def __init__(self, adress=1, port='/dev/ttyUSB2'):
        threading.Thread.__init__(self)

        with open('turbo.txt', 'w'):
            pass
        logging.basicConfig(filename="turbo.txt", level=logging.INFO)
        logging.info('Program started.')
        logging.basicConfig(level=logging.INFO)

        self.f = serial.Serial(port,9600)
        self.f.stopbits = 2
        self.adress = adress
        self.status = {} #Hold parameters to be accessible by gui
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
            response += a
        length = int(response[8:10])
        reply = response[10:10+length]
        crc = response[10+length:10+length+3]
        if crc:
            return reply
        else:
            return 'Error!'

    def crc_calc(self, command):
        crc = 0
        for s in command:
            crc +=  ord(s)
        crc = crc % 256
        crc_string = str(crc).zfill(3)
        return crc_string

    def read_rotation_speed(self):
        command = '398'
        reply = self.comm(command, True)
        val = int(reply)/60.0
        logging.warn(val)
        #command = '309'
        #reply = self.comm(command, True)
        #logging.warn(reply)       
        return(val)

    def read_gas_mode(self):
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
        command = '307'
        reply = self.comm(command, True)
        if int(reply) == 1:
            return True
        else:
            return False

    def turn_pump_on(self, off=False):
        if not off:
            command = '1001006111111'
        else:
            command = '1001006000000'
        self.comm(command, False)

    def read_temperature(self):
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
            time.sleep(0.5)
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

    mainpump = TurboDriver(adress=2)
    mainpump.start()

    tui = CursesTui(mainpump)
    tui.daemon = True
    tui.start()

