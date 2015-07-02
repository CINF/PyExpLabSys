#import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import MySQLdb
from scipy import optimize
from scipy import interpolate
import math

PEAK_FIT_WIDTH = 5


def fit_peak(time, mass, data):
    center = np.where(Data[:,0] > fit_values[mass])[0][0]
    Start = center -50 #Display range
    End = center + 50
    X_values = Data[Start:End,0]
    Y_values = Data[Start:End,1]
    center = np.where(Y_values == max(Y_values))[0][0]

    #Fitting range
    x_values = X_values[center-PEAK_FIT_WIDTH:center+PEAK_FIT_WIDTH]
    y_values = Y_values[center-PEAK_FIT_WIDTH:center+PEAK_FIT_WIDTH]
    
    fitfunc = lambda p, x: p[0]*math.e**(-1*((x-fit_values[mass]-p[2])**2)/p[1])
    errfunc = lambda p, x, y: fitfunc(p, x) - y # Distance to the target function
    p0 = [max(Y_values), 0.00001, 0] # Initial guess for the parameters
    try:
        p1, success = optimize.leastsq(errfunc, p0[:], args=(x_values, y_values),maxfev=10000) 
    except: # Fit failed
        p1 = p0
        success = 0
    usefull = (p1[0] > 20) and (p1[1] < 1e-4) and (success==1) # Only use the values if fit succeeded and peak has decent height
    if usefull:
        print p1
    #fig = plt.figure()
    #ax = fig.add_subplot(1, 1, 1)
    #ax.plot(X_values, Y_values, 'k-')
    #ax.plot(X_values, fitfunc(p1, X_values), 'r-')
    #ax.axvline(X_values[center-PEAK_FIT_WIDTH])
    #ax.axvline(X_values[center+PEAK_FIT_WIDTH])
    #plt.show()
    return usefull, p1

def x_axis_fit_func(p, time):
    mass = p[0] + p[1]* pow(time, p[2])
    return mass

def fit_x_axis(fit_values):
    errfunc = lambda p, x, y: x_axis_fit_func(p, x) - y # Distance to the target function
    p0 = [-0.01, 0.1, 2] # Initial guess for the parameters
    p1, success = optimize.leastsq(errfunc, p0[:], args=(fit_values.values(), fit_values.keys()), maxfev=10000)
    return p1

db = MySQLdb.connect(host="servcinf.fysik.dtu.dk", user="cinf_reader",passwd = "cinf_reader", db = "cinfdata")
cursor = db.cursor()
cursor.execute("SELECT x*1000000,y FROM xy_values_tof where measurement = 2667")
Data = np.array(cursor.fetchall())

fit_values = {}
fit_values[2] = 4.37
fit_values[4] = 6.1
fit_values[18] = 12.74
fit_values[28] = 15.84

i = 0
for mass in fit_values:
    usefull, p1_peak = fit_peak(fit_values[mass], mass, Data)
    fit_values[mass] = fit_values[mass] + p1_peak[2]

p1_x_axis = fit_x_axis(fit_values)

for mass in range(10, 180):
    times = np.arange(0, 45, 0.01) # Calculate all masses within a 45microsecond scan
    time_index = np.where(x_axis_fit_func(p1_x_axis, times) > mass)[0][0]
    flight_time = times[time_index]
    fit_values[mass] = flight_time
    usefull, p1_peak = fit_peak(flight_time, mass, Data)
    if usefull is True:
        fit_values[mass] = fit_values[mass] + p1_peak[2]
        p1_x_axis = fit_x_axis(fit_values)
        print mass
    else:
        del fit_values[mass]

fig = plt.figure()
ax = fig.add_subplot(2, 1, 1)
ax.plot(fit_values.values(), fit_values.keys() - x_axis_fit_func(p1_x_axis, fit_values.values()), 'bo')
ax = fig.add_subplot(2, 1, 2)
x_fit = np.arange(0, 45, 0.01)
ax.plot(fit_values.values(), fit_values.keys(), 'bo')
ax.plot(x_fit, x_axis_fit_func(p1_x_axis, x_fit), 'k-')
plt.show()

fig = plt.figure()
ax = fig.add_subplot(1, 1, 1)
ax.plot(x_axis_fit_func(p1_x_axis, Data[:,0]), Data[:,1], 'k-')
ax.set_xlim(1,200)
print p1_x_axis
plt.show()

