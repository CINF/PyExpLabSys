# -*- coding: utf-8 -*-
"""
Created on Tue Oct 21 08:49:40 2014

@author: aufn
"""
import time
import numpy as np

class ramp:
    def __init__(self,):
        date_str = "2014-10-30 14:30:00"
        time_tuple = time.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        start = time.mktime(time_tuple)
        #start = time.time()
        self.start_time = start
        
        date_str = "2014-10-30 23:59:59"
        time_tuple = time.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        end = time.mktime(time_tuple)
        #end = self.start_time + 3600*3
        self.end_time = end
        self.dutycycles = [0.0,0.0,0.0,0.0,0.0,0.0]
        
    def present(self,t):
        if self.start_time < t < self.end_time:
            self.dutycycles = [0.1,0.2,0.3,0.4,0.5,0.6]
        else:
            self.dutycycles = [0.0,0.0,0.0,0.0,0.0,0.0]
        return self.dutycycles

if __name__ == '__main__':
    R = ramp()
    t = list(np.linspace(time.time(),time.time()+3*24*3600,1000))
    y = []
    for t_i in t:
        y += [R.present(t_i)]
