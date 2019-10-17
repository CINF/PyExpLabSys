
"""GNU plot based plots direcly into a curses window

This module provides two classes for creating text plots, one for
creating a text plot as a text string :class:`.AsciiPlot` and one for
writing the resulting plot directly into a curses window,
:class:`.CursesAsciiPlot`, automatically adjusting the size of the
plot to the window.

:class:`.AsciiPlot` example:
----------------------------

.. code:: python

   from PyExpLabSys.common.text_plot import AsciiPlot
   import numpy

   x = numpy.linspace(0, 6.28, 100)
   y = numpy.sin(x)

   ascii_plot = AsciiPlot(title='Sine', xlabel='x', ylabel='y', size=(80, 24))
   text_plot = ascii_plot.plot(x, y)
   print(text_plot)

Produces the following output:

.. code:: text

                                          Sine                                     
                                                                                   
        1 +--------------------------------------------------------------------+   
          |         ***      ***        +        +         +         +         |   
      0.8 |-+     **            **                                           +-|   
      0.6 |-+   ***               *                                          +-|   
          |    **                  **                                          |   
      0.4 |-+ *                     **                                       +-|   
          |  *                        *                                        |   
      0.2 |**                          *                                     +-|   
        0 |*+                           **                                   +-|   
    y     |                              **                            **      |   
     -0.2 |-+                              *                          **     +-|   
          |                                 *                        *         |   
     -0.4 |-+                                **                     *        +-|   
          |                                   **                  **           |   
     -0.6 |-+                                   *               ***          +-|   
     -0.8 |-+                                    **            **            +-|   
          |         +         +         +        + ***     +***      +         |   
       -1 +--------------------------------------------------------------------+   
          0         1         2         3        4         5         6         7   
                                            x                                      

:class:`.CursesAsciiPlot` example
---------------------------------

.. code:: python

   import time
   import curses
   import numpy as np
   from PyExpLabSys.common.text_plot import CursesAsciiPlot

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
           win, title="Log of sine of time + 1.1", xlabel="Time [s]",
           logscale=True,
       )

       # Plot the sine to time since start and 10 sec a head
       while True:
           stdscr.clear()
           t0 = time.time() - t_start
           # Write the time right now to the main window
           stdscr.addstr(1, 3, 'T0: {:.2f}       '.format(t0))
           stdscr.refresh()
           x = np.linspace(t0, t0 + 10)
           y = np.sin(x) + 1.1
           ap.plot(x, y, legend="Sine")
           time.sleep(0.2)
   finally:
       curses.echo()
       curses.endwin()

"""

from subprocess import Popen, PIPE


class CursesAsciiPlot(object):
    """A Curses Ascii Plot"""

    def __init__(self, curses_win, **kwargs):
        """Initialize local variables

        Args:
            curses_win (curses-window-objects): The curses window to print the plot into

        For possible value for kwargs, see arguments for :meth:`.AsciiPlot.__init__`.
        """
        self.win = curses_win

        # Note, x and y sizes are reversed in curses, curses!!!
        size = list(self.win.getmaxyx()[::-1])

        # There is some problem writing to the last line of the window
        # so for now just don't
        size[1] -= 1

        self.ascii_plotter = AsciiPlot(size=size, **kwargs)

    def plot(self, *args, **kwargs):
        """Plot data to the curses window

        For an explanation of the arguments, see :meth:`.AsciiPlot.plot`.
        """
        data = self.ascii_plotter.plot(*args, **kwargs)
        self.win.clear()
        for line_num, line in enumerate(data.split('\n')):
            self.win.addstr(line_num, 0, line)
        self.win.refresh()


class AsciiPlot(object):
    """An Ascii Plot"""

    def __init__(self, title=None, xlabel=None, ylabel=None, logscale=False,
                 size=(80, 24), debug=False):
        """Initialize local varibles

        Args:
            title (str): The title of the plot if required
            xlabel (str): The xlabel of the plot if required
            ylabel (str): The ylabel of the plot if required
            logscale (bool): If the yaxis should use log scale
            size (tuple): A list or tuple with two integers indication the x and y size
                (i.e. number of columns and lines) of the plot
            debug (bool): Whether to show the command sent to gnuplot
        """
        self.size = size
        self.debug = debug

        # Open a process for gnuplot
        self.process = Popen(['gnuplot'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        self.read = self.process.stdout.read

        # Setup ascii output and size
        self.write("set term dumb {} {}\n".format(*size))

        # Set title and labels
        for string, name in ((title, 'title'), (xlabel, 'xlabel'), (ylabel, 'ylabel')):
            if string:
                string = string.replace('"', "'")
                self.write("set {} \"{}\"\n".format(name, string))

        # Set log scale if required
        if logscale:
            self.write("set logscale y\n")

        self.write("set out\n")        
        
    def write(self, string):
        r"""Write string to gnuplot

        String must be \n terminated
        """
        if self.debug:
            print(repr(string))
        self.process.stdin.write(string)    
        
    def plot(self, x, y, style='lines', legend=""):
        """Plot data

        Args:
            x (iterable): An iterable of floats or ints to plot
            y (iterable): An iterable of floats or ints to plot
            style (str): 'lines' or 'points'
            legend (str): The legend of the data (leave to empty string to skip)
        """
        # Header for sending data to gnuplot inline
        self.write("plot \"-\" with lines title \"{}\"\n".format(legend))

        # Create data string and send
        data = '\n'.join(["%s %s" % pair for pair in zip(x, y)])
        self.write(data + '\n')
        self.write("e\n")  # Terminate column

        # The first char is a form feed
        self.read(1)
        out = self.read(self.size[0] * self.size[1])
        while out[-1] != '\n':
            out += self.read(1)
        return out


if __name__ == "__main__":
    import time
    import numpy as np
    import curses

    # Init and clear
    stdscr = curses.initscr()
    stdscr.clear()
    curses.noecho()

    # Make plot window
    screen_size = stdscr.getmaxyx()
    win = curses.newwin(screen_size[0] - 3, screen_size[1], 3, 0)

    t_start = time.time()
    try:
        # Create the Curses Ascii Plotter
        ap = CursesAsciiPlot(
            win, title="Log of sine of time", xlabel="Time [s]",
            logscale=True,
        )

        # Plot the sine to time since start and 10 sec a head
        while True:
            stdscr.clear()
            t0 = time.time() - t_start
            stdscr.addstr(1, 3, 'T0: {:.2f}       '.format(t0))
            stdscr.refresh()
            x = np.linspace(t0, t0 + 10)
            y = np.sin(x) + 1.1
            ap.plot(x, y, legend="Sine")
            time.sleep(0.2)
    finally:
        curses.echo()
        curses.endwin()
