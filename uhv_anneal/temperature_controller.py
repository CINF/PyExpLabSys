import time
import ParallelPortBinaryOut
import socket
import PID
import threading
import curses

def read_value(keyword):
    HOST, PORT = "130.225.87.230", 9999 #uhvanneal IP
    data = "read_" + keyword
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(data + "\n", (HOST, PORT))
    received = sock.recv(1024)
    temp = float(received)
    return temp

class status_output(threading.Thread):

    def __init__(self, heater_instance, setpoint):
        threading.Thread.__init__(self)
        
        self.heater = heater_instance
        self.setpoint = setpoint

        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.screen.keypad(1)
        self.screen.nodelay(1)
        
    def run(self):
        while True:
            headline = "Status of the UHV furnace"
            self.screen.addstr(1, 1, headline, curses.A_BOLD)
            
            setpoint_string = "Current setpoint: " + str(self.setpoint)
            self.screen.addstr(2, 1, setpoint_string)
            
            temperature_1 = "Temperature 1: " + str(read_value("temperature_1"))
            self.screen.addstr(3, 1, temperature_1)
            
            temperature_2 = "Temperature 2: " + str(read_value("temperature_2"))
            self.screen.addstr(4, 1, temperature_2)
            
            temperature_outside = "Temperature outside: " + str(read_value("temperature_outside"))
            self.screen.addstr(5, 1, temperature_outside)
                       
            n = self.screen.getch()
            if n == ord('q'):
                self.screen.addstr(6, 1, "Quitting...", curses.A_BOLD)
                heater.stop = True
                                
            self.screen.refresh()
            time.sleep(1)

    def stop(self):
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()

class heating_control():

    def __init__(self):
        self.parallel = ParallelPortBinaryOut.ParallelPortBinaryOut()
        self.pid_control = PID.PID()
        self.heart_beat = 10
        self.stop = False
        
    def set_setpoint(self,setpoint):
        self.setpoint = setpoint
        return self.setpoint

    def control_temperature(self,setpoint):
        self.stop = False
        while self.stop == False:
            self.pid_control.UpdateSetpoint(setpoint)

            temperature_outside = read_value("temperature_outside")
            temperature_1 = read_value("temperature_1")
            temperature_2 = read_value("temperature_2")
            #print temperature_1
            #print temperature_2
            #print temperature_outside
            self.pid_output = self.pid_control.WantedPower(temperature_1)
            self.parallel.setState(0,True)
            time.sleep(self.pid_output/self.heart_beat)
            self.parallel.setState(0,False)
            time.sleep(self.heart_beat-(self.pid_output/self.heart_beat))

if __name__ == "__main__":
    temperature_setpoint = 0
    heater = heating_control()
    
    printer = status_output(heater,temperature_setpoint)
    printer.daemon = True
    printer.start()
    
    heater.control_temperature(temperature_setpoint)
    
    printer.stop()
