# pylint: disable=E1101
""" Program to fix x-axis on TOF-spectra """
from __future__ import print_function
import sys
import matplotlib.pyplot as plt
import numpy as np
import mysql.connector
from scipy import optimize
import math


from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

#PEAK_FIT_WIDTH = 5


def fit_peak(time, mass, data, fit_values):
    """ Fit a gaussian peak """
    values = {}
    center = np.where(data[:, 0] > fit_values[mass])[0][0]
    values['x'] = data[center - 75:center + 75, 0]
    values['y'] = data[center - 75:center + 75, 1]
    center = np.where(values['y'] == max(values['y']))[0][0]
    fitfunc = lambda p, x: p[0]*math.e**(-1*((x-fit_values[mass]-p[2])**2)/p[1])
    errfunc = lambda p, x, y: fitfunc(p, x) - y # Distance to the target function
    p0 = [max(values['y']), 0.00001, 0] # Initial guess for the parameters
    try:
        p1, success = optimize.leastsq(errfunc, p0[:], args=(values['x'], values['y']),
                                       maxfev=10000)
    except: # Fit failed
        p1 = p0
        success = 0
    # Only use the values if fit succeeded and peak has decent height
    usefull = (p1[0] > 15) and (p1[1] < 1e-3) and (success==1)
    if usefull:
        print(p1)
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(values['x'], values['y'], 'k-')
    ax.plot(values['x'], fitfunc(p1, values['x']), 'r-')
    ax.plot(values['x'], fitfunc(p0, values['x']), 'c-')
    #ax.axvline(values['x'][center-PEAK_FIT_WIDTH])
    #ax.axvline(values['x'][center+PEAK_FIT_WIDTH])
    plt.show()
    return usefull, p1

def x_axis_fit_func(p, time):
    #mass = p[1]* pow(time-p[0], p[2])
    mass = p[1]* pow(time-p[0], 2)
    return mass

def fit_x_axis(fit_values):
    """ Fit a quadratic dependence for the mass versus time relation """
    errfunc = lambda p, x, y: x_axis_fit_func(p, x) - y # Distance to the target function
    fit_params = [0.1, 0.1, 2] # Initial guess for the parameters
    fitted_params, success = optimize.leastsq(errfunc, fit_params[:],
                                              args=(list(fit_values.values()), list(fit_values.keys())),
                                              maxfev=10000)
    return fitted_params

def main():
    """Main function """
    spectrum_number = sys.argv[1]
    print(spectrum_number)

    database = mysql.connector.connect(host="servcinf-sql.fysik.dtu.dk", user="tof",
                                       passwd="tof", db="cinfdata")
    cursor = database.cursor()
    cursor.execute("SELECT x * 1000000,y FROM xy_values_tof where measurement = " +
                   str(spectrum_number))
    data = np.array(cursor.fetchall())

    fit_values = {}
    fit_values[2] = 3.80
    fit_values[4] = 5.53
    fit_values[18] = 12.17
    fit_values[28] = 15.278

    fit_values = {}
    fit_values[2.01565] = 3.80
    fit_values[4.00260] = 5.53
    fit_values[18.01056] = 12.17
    fit_values[184.0347] = 39.76
    for mass in fit_values:
        usefull, p1_peak = fit_peak(fit_values[mass], mass, data, fit_values)
        fit_values[mass] = fit_values[mass] + p1_peak[2]
    p1_x_axis = fit_x_axis(fit_values)

    """
    for mass in fit_values:
        usefull, p1_peak = fit_peak(fit_values[mass], mass, data, fit_values)
        fit_values[mass] = fit_values[mass] + p1_peak[2]
    p1_x_axis = fit_x_axis(fit_values)

    for mass in range(10, 200):
        times = np.arange(0, 45, 0.01) # Calculate all masses within a 45microsecond scan
        time_index = np.where(x_axis_fit_func(p1_x_axis, times) > mass)[0][0]
        flight_time = times[time_index]
        fit_values[mass] = flight_time
        usefull, p1_peak = fit_peak(flight_time, mass, data, fit_values)
        if usefull is True:
            fit_values[mass] = fit_values[mass] + p1_peak[2]
            p1_x_axis = fit_x_axis(fit_values)
            print(mass)
        else:
            print('Unusefull mass: ' + str(mass))
            del fit_values[mass]
    """
    fig = plt.figure()
    axis = fig.add_subplot(2, 1, 1)
    axis.plot(list(fit_values.values()), list(fit_values.keys()) -
              x_axis_fit_func(p1_x_axis, list(fit_values.values())), 'bo')
    axis = fig.add_subplot(2, 1, 2)
    x_fit = np.arange(0, 45, 0.01)
    axis.plot(list(fit_values.values()), list(fit_values.keys()), 'bo')
    axis.plot(x_fit, x_axis_fit_func(p1_x_axis, x_fit), 'k-')
    plt.show()

    fig = plt.figure()
    axis = fig.add_subplot(1, 1, 1)
    axis.plot(x_axis_fit_func(p1_x_axis, data[:, 0]), data[:, 1], 'k-')
    axis.set_xlim(1, 300)
    print(p1_x_axis)
    plt.show()

    query = ('update measurements_tof set time=time, tof_p1_0=' + str(p1_x_axis[0]) +
             ', tof_p1_1=' + str(p1_x_axis[1]) + ', tof_p1_2=' + str(p1_x_axis[2]) +
             ' where id = ' + str(spectrum_number))
    if sys.argv[2] == 'yes':
        print(query)
        cursor.execute(query)

        
if __name__ == '__main__':
    main()
