import matplotlib
matplotlib.use('GTKAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg


import numpy
class NPointRunning:
    """ A N point running plot """

    def __init__(self, number_of_points):
        """ Init plot """
        # Assign settings to variable
        self.number_of_points = number_of_points

        self.x = numpy.arange(0, 2*numpy.pi ,0.01)
        self.line = None
        self.background = None
        self.count = 0

        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.fig.set_facecolor('white')
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasGTKAgg(self.fig)
        self.canvas.draw()

        self._reinit_plot()

    def _reinit_plot(self):
        self.line, = self.ax.plot(self.x, numpy.sin(self.x))#, animated=True)
        self.canvas.draw()
        #self.ax.set_xlim(0, self.number_of_points - 1)
        #self.ax.set_ylim(0, 1)
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)
        print 'jj'

    def _push_new_point(self):
        self.canvas.restore_region(self.background)
        self.line.set_ydata(numpy.sin(self.x + self.count/10.0))
        self.ax.draw_artist(self.line)
        self.canvas.blit(self.ax.bbox)
        self.count += 1

    def push_new_point(self):
        print 'test'
