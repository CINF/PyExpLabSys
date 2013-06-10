import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import scipy
import scipy.ndimage
from scipy import interpolate
import numpy as np

import socket
import cv
import time


class optimize():

    def __init__(self, top, bottom):
        self.top = top
        self.bottom = bottom
        self.camera = cv.CaptureFromCAM(0)
        cv.SetCaptureProperty(self.camera,cv.CV_CAP_PROP_FRAME_WIDTH,320)
        cv.SetCaptureProperty(self.camera,cv.CV_CAP_PROP_FRAME_HEIGHT,240)


    def snapshot(self, name):
        error = True
        while error:
            error = False
            f = cv.QueryFrame(self.camera)
            cv.SaveImage(name + '.png',f)
            img = scipy.misc.imread(name + '.png')
            #img2 = scipy.asarray(f[:,:])
            print type(img)
            #for i in range(0,img.shape[0],4):
            #    for j in range(0,img.shape[1],10):
            #        if ((img[i,j,0] - 10) > img[i,j,1]):
            #            error = True
        return(img)

    def find_coordinates(self):
        img = self.snapshot('coords')
        top = self.top
        bottom = self.bottom

        fig = plt.figure()
        axis = fig.add_subplot(1,1,1)

        img = img[:,:,0] # Image is black and white, remove color information

        a = plt.imshow(img,cmap=plt.cm.gray)
        b = plt.plot([top[0],bottom[0]],[top[1],bottom[1]],'k-')
        axis.set_ylim(240,0)
        axis.set_xlim(0,320)
        c = plt.Rectangle([279,43],38,20,color='b',fill=False)
        fig.gca().add_artist(c)
        d = plt.Rectangle([279,177],38,20,color='b',fill=False)
        fig.gca().add_artist(d)
        #axis.set_xticks([])
        #axis.set_yticks([])
        plt.savefig('coords.png')

    def update_trace(self):
        reactor_length = 27.0#mm
        reactor_pixels = ((bottom[0]-top[0])**2 + (bottom[1]-top[1])**2)**0.5
        assert reactor_pixels >= abs(top[0]-bottom[0])
        pix_pr_mm = reactor_pixels / reactor_length

        img = self.snapshot('thermo')
        fig = plt.figure()
        axis = fig.add_subplot(1,1,1)
        #img = scipy.misc.imread('thermo.png')
        img = img[:,:,0] # Image is black and white, remove color information

        #Adapted from: http://stackoverflow.com/questions/7878398/how-to-extract-an-arbitrary-line-of-values-from-a-numpy-array
        num_points = 500
        x = np.linspace(top[1], bottom[1], num_points)
        y = np.linspace(top[0], bottom[0], num_points)
        # Extract the values along the line, using cubic interpolation
        zi = scipy.ndimage.map_coordinates(img, np.vstack((x,y)))

        zi = zi + 22 #OFFSET ON CAMERA

        x_range = scipy.arange(0,27,27.0/num_points)

        axis.plot(x_range, zi)
        #Reactor position: 2mm to 12mm from the top
        axis.axvline(2,color='r')
        axis.axvline(12,color='r')
        axis.set_xlim(0,reactor_length)
        plt.savefig('slice.png')
        return max(zi[num_points*2.0/27:num_points*12.0/27]),min(zi[num_points*2.0/27:num_points*12.0/27])

if __name__ == '__main__':
    top = (123, 88)
    bottom = (240, 87)
    optimizer = optimize(top=top, bottom=bottom)

    optimizer.find_coordinates()

    for i in range(0,10):
        print optimizer.update_trace()

