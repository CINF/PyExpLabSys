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
import subprocess

import sys
sys.path.append('../')
import agilent_34972A as multiplexer

class optimize():

    def __init__(self, top, bottom):
        self.top = top
        self.bottom = bottom
        self.low_range_temp = 0
        self.high_range_temp = 256
        self.camera = cv.CaptureFromCAM(0)
        cv.SetCaptureProperty(self.camera,cv.CV_CAP_PROP_FRAME_WIDTH,320)
        cv.SetCaptureProperty(self.camera,cv.CV_CAP_PROP_FRAME_HEIGHT,240)
        self.mul = multiplexer.Agilent34972ADriver()

    def update_heater_iv(self):
        data = self.mul.read_single_scan()
    
        heaters = {}
        heaters['I'] = {}
        heaters['V'] = {}
    
        heaters['I'][1] = data[0]
        heaters['I'][2] = data[2]
        heaters['I'][3] = data[4]
        heaters['V'][1] = data[1]
        heaters['V'][2] = data[3]
        heaters['V'][3] = data[5]
        print 'Heater 1, I: ' + str(data[0]) + 'A, V: ' +  str(data[1])  + 'V, R: ' + str(data[1]/data[0]) + 'ohm, P: ' + str(data[1]*data[0]) + 'W'
        print 'Heater 2, I: ' + str(data[2]) + 'A, V: ' +  str(data[3])  + 'V, R: ' + str(data[3]/data[2]) + 'ohm, P: ' + str(data[3]*data[2]) + 'W'
        print 'Heater 3, I: ' + str(data[4]) + 'A, V: ' +  str(data[5])  + 'V, R: ' + str(data[5]/data[4]) + 'ohm, P: ' + str(data[5]*data[4]) + 'W'
        print 'Total power: ' + str(data[5]*data[4] + data[3]*data[2] + data[1]*data[0]) + 'W'
        return heaters


    def snapshot(self, name):
        error = True
        while error:
            error = False
            f = cv.QueryFrame(self.camera)
            f = cv.QueryFrame(self.camera)
            f = cv.QueryFrame(self.camera)
            cv.SaveImage(name + '.png',f)
            img = scipy.misc.imread(name + '.png')
            #img2 = scipy.asarray(f[:,:])
            #for i in range(0,img.shape[0],4):
            #    for j in range(0,img.shape[1],10):
            #        if ((img[i,j,0] - 10) > img[i,j,1]):
            #            error = True
        return(img)

    def find_coordinates(self):
        t = time.time()
        img = self.snapshot('coords')
        top = self.top
        bottom = self.bottom

        fig = plt.figure()
        axis = fig.add_subplot(1,1,1)
        img = img[:,:,0] # Image is black and white, remove color information

        a = plt.imshow(img,cmap=plt.cm.gray)
        b = plt.plot([top[0],bottom[0]],[top[1],bottom[1]],'b-')
        axis.set_ylim(240,0)
        axis.set_xlim(0,320)
        c = plt.Rectangle([279,43],38,20,color='b',fill=False)
        fig.gca().add_artist(c)
        d = plt.Rectangle([279,177],38,20,color='b',fill=False)
        fig.gca().add_artist(d)
        #axis.set_xticks([])
        #axis.set_yticks([])
        plt.savefig('coords.png')

    def set_brightness_and_contrast(self, brightness, contrast):
        subprocess.check_output(['uvcdynctrl', '--set=Contrast', str(contrast)])
        subprocess.check_output(['uvcdynctrl', '--set=Brightness', str(brightness)])

    def ocr(self, filename):
        subprocess.check_output(["convert", "-crop", "60x33+650+154", filename, '_' + filename])    #convert -crop 60x35+650+154 coords.png coords.png 
        #subprocess.check_output(['convert', '-negate', '_' + filename, '_' + filename])
        subprocess.check_output(['convert', '-contrast', '-contrast', '-contrast', '-contrast', '_' + filename, '_' + filename])
        subprocess.check_output(['convert', '_' + filename, '_' + filename + '.pgm'])
        high = subprocess.check_output(['ocrad', '--filter', 'numbers_only', '_' + filename + '.pgm'])
        high_number = int(high)
        
        subprocess.check_output(["convert", "-crop", "60x32+650+411", filename, '_' + filename])
        #subprocess.check_output(['convert', '-negate', '_' + filename, '_' + filename])
        subprocess.check_output(['convert', '-contrast', '-contrast', '-contrast', '-contrast', '_' + filename, '_' + filename])
        subprocess.check_output(['convert', '_' + filename, '_' + filename + '.pgm'])
        low = subprocess.check_output(['ocrad', '--filter', 'numbers_only', '_' + filename + '.pgm'])
        low_number = int(low)
        return (high_number, low_number)

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

        image_dyn_range = 235 - 16 # The number of values that span the range of the camera
        
        scale = (self.high_range_temp - self.low_range_temp)/256.0
        zi = zi * scale + self.low_range_temp

        x_range = scipy.arange(0,27,27.0/num_points)

        axis.plot(x_range, zi)
        #Reactor position: 2mm to 12mm from the top
        axis.axvline(2,color='r')
        axis.axvline(12,color='r')
        axis.set_xlim(0,reactor_length)
        plt.savefig('slice.png')
        return max(zi[num_points*2.0/27:num_points*12.0/27]),min(zi[num_points*2.0/27:num_points*12.0/27])

if __name__ == '__main__':
    top = (145,75)
    bottom = (250, 75)
    optimizer = optimize(top=top, bottom=bottom)
    for i in range(2,7):
        for j in range(1,6):
            optimizer.set_brightness_and_contrast(brightness=(i*1000), contrast=(j*100))
            time.sleep(3)
            optimizer.find_coordinates()
            (high, low) = optimizer.ocr('coords.png')
            print i, j, high, low

    """
    optimizer.low_range_temp  = low
    optimizer.high_range_temp = high
    optimizer.update_heater_iv()
    trace = optimizer.update_trace()
    print trace
    print max(trace) - min(trace)
    """
