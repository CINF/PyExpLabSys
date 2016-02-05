# pylint: disable=E1101
""" The application will integrate peaks areas of a number
    of spectrums as function of time """
#from __future__ import print_function
import matplotlib.pyplot as plt
import numpy as np
import mysql.connector
import pickle
import math
import time
from lmfit import Model
from matplotlib.backends.backend_pdf import PdfPages

PEAK_FIT_WIDTH = 25
DATEPLOT_TABLE = 'dateplots_mgw'
DATEPLOT_TYPE = 273
MEASUREMENT_TABLE = 'measurements_tof'
XY_VALUES_TABLE = 'xy_values_tof'
NORMALISATION_FIELD = 'tof_iterations'

def gaussian(x, amp, cen, wid):
    """ Gaussian function for fitting """
    return amp * math.e ** (-1 * ((x - cen) ** 2) / wid)
    
def double_gaussian(x, amp, cen, wid, amp2, cen2, wid2):
    """ Double Gaussian function for fitting """
    peak1 = gaussian(x, amp, cen, wid)
    peak2 = gaussian(x, amp2, cen2, wid2)
    return peak1 + peak2

def fit_peak(flight_times, data, axis=None):
    """ Fit a peak using lmfit """
    center_time = np.mean(flight_times)
    center = np.where(data[:, 0] > center_time)[0][0]
    Start = center - 100 #Display range
    End = center + 100
    X_values = data[Start:End, 0]
    Y_values = data[Start:End, 1]
    center = np.where(Y_values == max(Y_values))[0][0]

    background = np.mean(Y_values[center-3*PEAK_FIT_WIDTH:center-2*PEAK_FIT_WIDTH])
    print('Background: ' + str(background))

    fit_width = PEAK_FIT_WIDTH + PEAK_FIT_WIDTH * (len(flight_times)-1) * 0.45
    #Fitting range
    x_values = X_values[center-fit_width:center+fit_width]
    y_values = Y_values[center-fit_width:center+fit_width] - background

    if len(flight_times) == 1:
        gmod = Model(gaussian)
        result = gmod.fit(Y_values, x=X_values, amp=max(Y_values),
                          cen=flight_times[0], wid=0.0000025)
        fit_results = [(result.params['amp'].value, result.params['wid'].value,
                        result.params['cen'].value)]

    if len(flight_times) == 2:
        center1 = np.where(data[:, 0] > flight_times[0])[0][0]
        max1 = max(data[center1-10:center1+10, 1])

        center2 = np.where(data[:, 0] > flight_times[1])[0][0]
        max2 = max(data[center2-10:center2+10, 1])

        gmod = Model(double_gaussian)
        result = gmod.fit(Y_values, x=X_values, amp=max1, cen=flight_times[0], wid=0.0000025,
                          amp2=max2, cen2=flight_times[1], wid2=0.0000025)
        fit_results = [(result.params['amp'].value, result.params['wid'].value,
                        result.params['cen'].value),
                       (result.params['amp'].value, result.params['wid'].value,
                        result.params['cen'].value)]
    usefull = result.success
        
    if axis is not None:
        axis.plot(X_values, Y_values, 'k-')
        if len(flight_times) == 1:
            #ax.plot(X_values, result.init_fit+background, 'k--')
            axis.plot(X_values, gaussian(X_values, result.params['amp'].value,
                                         result.params['cen'].value,
                                         result.params['wid'].value) + background, 'r-')
        if len(flight_times) == 2:
            #ax.plot(X_values, result.init_fit, 'k--')
            axis.plot(X_values, double_gaussian(X_values, result.params['amp'].value,
                                                result.params['cen'].value,
                                                result.params['wid'].value,
                                                result.params['amp2'].value,
                                                result.params['cen2'].value,
                                                result.params['wid2'].value)+background, 'r-')

        axis.axvline(X_values[center-fit_width])
        axis.axvline(X_values[center+fit_width])
        axis.annotate(str(time), xy=(.05, .85), xycoords='axes fraction', fontsize=8)
        axis.annotate("Usefull: " + str(usefull), xy=(.05, .7),
                      xycoords='axes fraction', fontsize=8)
        #plt.show()
    return usefull, fit_results


def main(x_values):
    """ Main function """
    conn = mysql.connector.connect(host="servcinf-sql.fysik.dtu.dk", user="cinf_reader",
                                   passwd="cinf_reader", db="cinfdata")
    cursor = conn.cursor()

    spectrum_numbers = range(4160, 4165)

    dateplot_values = []
    timestamps = []

    for x in x_values:
        x_values[x]['peak_area'] = {}
        x_values[x]['errors'] = {}
        for name in x_values[x]['names']:
            x_values[x]['peak_area'][name] = []
            x_values[x]['errors'][name] = []

    pdf_file = PdfPages('multipage.pdf')
    for spectrum_number in spectrum_numbers:
        print(spectrum_number)
        t = time.time()
        try:
            Data = pickle.load(open(str(spectrum_number) + '.p', 'rb'))
        except (IOError, EOFError):
            cursor.execute('SELECT x*1000000,y FROM ' + XY_VALUES_TABLE +  ' where measurement = ' + str(spectrum_number))
            Data = np.array(cursor.fetchall())
            pickle.dump(Data, open(str(spectrum_number) + '.p', 'wb'))
        print(time.time() - t)

        try:
            query = 'select time, unix_timestamp(time), ' + NORMALISATION_FIELD + ' from '
            query += MEASUREMENT_TABLE + ' where id = "' + str(spectrum_number) + '"'
        except NameError: # No normalisation
            query = 'select time, unix_timestamp(time), 1 from ' + MEASUREMENT_TABLE + ' where id = "' + str(spectrum_number) + '"'
        cursor.execute(query)
        spectrum_info = cursor.fetchone()

        query = 'SELECT unix_timestamp(time), value FROM ' + DATEPLOT_TABLE
        query += ' where type = ' + str(DATEPLOT_TYPE) + ' and time < "'
        query += str(spectrum_info[0]) + '" order by time desc limit 1';
        cursor.execute(query)
        before_value = cursor.fetchone()
        time_before = spectrum_info[1] - before_value[0]
        assert time_before > 0

        query = 'SELECT unix_timestamp(time), value FROM ' + DATEPLOT_TABLE
        query +=' where type = ' + str(DATEPLOT_TYPE) + ' and time > "'
        query += str(spectrum_info[0]) + '" order by time limit 1';
        cursor.execute(query)
        after_value = cursor.fetchone()
        time_after = after_value[0] - spectrum_info[1]
        assert time_before > 0

        calculated_temp = (before_value[1] * time_before + after_value[1] * time_after) / (time_after + time_before)
        dateplot_values.append(calculated_temp)

        i = 0
        pdffig = plt.figure()
        for x in x_values:
            i = i + 1
            axis = pdffig.add_subplot(2, 2, i)
            if i == 1:
                axis.text(0, 1.2, 'Spectrum id: ' + str(spectrum_number),
                          fontsize=12, transform=axis.transAxes)
                axis.text(0, 1.1, 'Sweeps: {0:.2e}'.format(spectrum_info[2]),
                          fontsize=12, transform=axis.transAxes)
            usefull, results = fit_peak(x_values[x]['flighttime'], Data, axis)

            for i in range(0, len(x_values[x]['names'])):
                name = x_values[x]['names'][i]
                area = math.sqrt(math.pi)*results[i][0] * math.sqrt(results[i][1])
                if usefull:
                    print name
                    x_values[x]['peak_area'][name].append(area * 2500 / spectrum_info[2])
                    x_values[x]['errors'][name].append(math.sqrt(area * 2500) /
                                                       spectrum_info[2])
                else:
                    x_values[x]['peak_area'][name].append(None)
                    x_values[x]['errors'][name].append(None)
                print(usefull)

        timestamps.append(spectrum_info[1])
        plt.savefig(pdf_file, format='pdf')
        plt.close()
    pdf_file.close()

    timestamps[:] = [t - timestamps[0] for t in timestamps]

    fig = plt.figure()
    axis = fig.add_subplot(1, 1, 1)

    for x in x_values:
        for i in range(0, len(x_values[x]['names'])):
            name = x_values[x]['names'][i]
            try:
                axis.errorbar(timestamps, x_values[x]['peak_area'][name], linestyle='-',
                              marker='o', label=x_values[x]['names'][i],
                              yerr=x_values[x]['errors'][name])
            except TypeError: # Cannot plot errorbars on plots with missing points
                axis.plot(timestamps, x_values[x]['peak_area'][name], linestyle='-', marker='o', label=str(x))

    axis2 = axis.twinx()
    axis2.plot(timestamps, dateplot_values, 'k-', label='test')

    axis.set_ylabel('Integraged peak area')
    axis2.set_ylabel('Temperature')
    axis.set_xlabel('Time / s')
    #axis.set_yscale('log')

    axis.legend(loc='upper left')

    plt.show()

    #print('----')
    #print(dateplot_values)
    #print('----')
    #print(peak_areas)
    #print('----')


if __name__ == '__main__':
    X_VALUES = {}
    X_VALUES['M4'] = {}
    X_VALUES['M4']['flighttime'] = [5.53]
    X_VALUES['M4']['names'] = ['He']

    X_VALUES['11.46'] = {}
    X_VALUES['11.46']['flighttime'] = [11.455, 11.467]
    X_VALUES['11.46']['names'] = ['11.46-low', '11.46-high']

    X_VALUES['11.82'] = {}
    X_VALUES['11.82']['flighttime'] = [11.81, 11.831]
    X_VALUES['11.82']['names'] = ['11.82-low', '11.82-high']
    #Todo: Also include fit-information such as exact peak position
    
    main(X_VALUES)
