import sys
import gtk, gobject
import matplotlib
matplotlib.use('GTKagg')
import pylab as p
#import matplotlib.numerix as nx
import numpy as nx
import time

ax = p.subplot(111)
canvas = ax.figure.canvas

# for profiling
tstart = time.time()

# create the initial line
x = nx.arange(0,2*nx.pi,0.01)
size = len(x)
line, = p.plot(x, nx.sin(x), animated=True)

# save the clean slate background -- everything but the animated line
# is drawn and saved in the pixel buffer background
background = canvas.copy_from_bbox(ax.bbox)

def update_line(*args):
    time.sleep(0.1)
    # restore the clean slate background
    canvas.restore_region(background)
    # update the data
    line.set_ydata(nx.sin(x+update_line.cnt/10.0))
    # just draw the animated artist
    ax.draw_artist(line)
    # just redraw the axes rectangle
    canvas.blit(ax.bbox)

    #if update_line.cnt > 50:
        # print the timing info and quit
    print 'Points: {0} FPS: {1}'.format(
        size, update_line.cnt/(time.time()-tstart))

    update_line.cnt += 1
    return True
update_line.cnt = 1

gobject.idle_add(update_line)
p.show()
