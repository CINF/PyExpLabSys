import matplotlib
matplotlib.use('GTK')
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg# as\
#    FigureCanvas


class NPointRunning(FigureCanvasGTKAgg):
    """ A N point running plot """

    def __init__(self):
        fig = Figure(figsize=(5, 4), dpi=100)
        fig.set_facecolor('white')
        self.ax = fig.add_subplot(111)
        FigureCanvasGTKAgg.__init__(self, fig)

        self.x = range(100)
        self.y = [None]*100

    def _reinit_plot(self):
        pass

    def push_new_point(self, arguments):
        pass

