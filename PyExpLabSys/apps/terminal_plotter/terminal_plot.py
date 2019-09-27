"""Simple script to plot in terminal the response of any value
logged via a DateDataPullSocket versus time.

Requires numpy in python2 and gnuplot
sudo apt-get update
sudo apt-get install gnuplot

# Example parameters:
HOSTNAME = 'rasppi98'
SOCKETNAME = 'omicron_pvci_pull'
CODENAME = 'omicron_ana_pressure'
LOGSCALE = True
"""
import sys
import time
import curses
import threading
import numpy as np
from PyExpLabSys.common.text_plot import CursesAsciiPlot
from PyExpLabSys.common.socket_clients import DateDataPullClient

if len(sys.argv) == 2:
    points = int(sys.argv[1])
else:
    points = 50

HOSTNAME = 'rasppi98'
SOCKETNAME = 'omicron_pvci_pull'
CODENAME = 'omicron_prep_pressure'
LOGSCALE = False

class DataClient(threading.Thread):
    """Maintain a numpy queue of newest `size` data points"""
    def __init__(self, hostname, socketname, codename, size=100):
        """Initialize"""
        threading.Thread.__init__(self)
        self.client = DateDataPullClient(hostname, socketname)
        self.codename = codename
        self.size = size
        self.counter = 0
        self.values = np.zeros((size, 2))
        self.values[:] = np.nan
        self.t_start = self.client.get_field(self.codename)[0]
        self.last_values = [-1, -1]
        self.new = None
        self.running = True
        self.update()

    def update(self):
        """Update values"""
        values = self.client.get_field(self.codename)
        # If value is new
        if values[0] > self.last_values[0]:
            self.last_values = values
            if self.counter < self.size:
                self.values[self.counter, :] = values[0] - self.t_start, values[1]
                self.counter += 1
            else:
                self.values[:-1, :] = self.values[1:, :]
                self.values[-1, :] = values[0] - self.t_start, values[1]
            self.new = True

    def run(self):
        """Continuously query for new values"""
        while self.running:
            self.update()
            time.sleep(0.04)

    def stop(self):
        """Exit main loop"""
        self.running = False

    def get_values(self):
        """Return non-NaN values"""
        index = np.isfinite(self.values)[:, 0]
        if self.new:
            status = True
            self.new = False
        else:
            status = False
        return self.values[index], status

# Setup communication with data socket
client = DataClient(HOSTNAME, SOCKETNAME, CODENAME, size=100)
client.start()

# Init and clear
stdscr = curses.initscr()
stdscr.clear()
curses.noecho()

# Make plot window
screen_size = stdscr.getmaxyx()

# Make the plot a little smaller than the main window, to allow a
# littel space for text at the top
win = curses.newwin(screen_size[0] - 3, screen_size[1], 3, 0)
t_start = time.time()
try:
    # Create the Curses Ascii Plotter
    ap = CursesAsciiPlot(
        win, title="Logging: {}/{}/{}".format(HOSTNAME, SOCKETNAME, CODENAME), xlabel="Time [s]",
        logscale=LOGSCALE,
    )
    # Plot the sine to time since start and 10 sec a head
    while True:
        #stdscr.clear() # Only neccessary if characters on a line isn't completely overwritten
        t0 = time.time() - t_start
        # Write the time right now to the main window
        stdscr.addstr(1, 3, 'T0: {:.2f}       '.format(t0))
        stdscr.refresh()
        values, new = client.get_values()
        if new:
            x = values[:, 0]
            y = values[:, 1]
            stdscr.addstr(2, 3, 'T: {:.2f}s   Last value: {}       '.format(x[-1], y[-1]))
            stdscr.refresh()
            ap.plot(x, y, legend="Data")
        time.sleep(0.2)
finally:
    client.stop()
    curses.echo()
    curses.endwin()
