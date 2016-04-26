# pylint: disable=E1101
""" The application will integrate peaks areas of a number
    of spectrums as function of time """
from __future__ import print_function
import matplotlib.pyplot as plt
import numpy as np
import mysql.connector
#import MySQLdb as mysql
import pickle
import math
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
    index = {}
    #Find index for 'center' time
    index['center'] = np.where(data[:, 0] > np.mean(flight_times))[0][0]
    index['start'] = index['center'] - 100 #Display range
    index['end'] = index['center'] + 100
    values = {}
    values['x'] = data[index['start']:index['end'], 0]
    values['y'] = data[index['start']:index['end'], 1]
    center = np.where(values['y'] == max(values['y']))[0][0]

    background = np.mean(values['y'][center-3*PEAK_FIT_WIDTH:center-2*PEAK_FIT_WIDTH])
    print('Background: ' + str(background))
    #TODO: Background should be fitted, lmfit can do this
    
    fit_width = PEAK_FIT_WIDTH + PEAK_FIT_WIDTH * (len(flight_times)-1) * 0.45
    #Fitting range
    values['x_fit'] = values['x'][center-fit_width:center+fit_width]
    values['y_fit'] = values['y'][center-fit_width:center+fit_width] - background

    if len(flight_times) == 1:
        gmod = Model(gaussian)
        result = gmod.fit(values['y_fit'], x=values['x_fit'], amp=max(values['y_fit']),
                          cen=flight_times[0], wid=0.0000025)
        fit_results = [(result.params['amp'].value, result.params['wid'].value,
                        result.params['cen'].value)]

    if len(flight_times) == 2:
        center1 = np.where(data[:, 0] > flight_times[0])[0][0]
        max1 = max(data[center1-10:center1+10, 1])

        center2 = np.where(data[:, 0] > flight_times[1])[0][0]
        max2 = max(data[center2-10:center2+10, 1])

        gmod = Model(double_gaussian)
        result = gmod.fit(values['y'], x=values['x'], amp=max1, cen=flight_times[0],
                          wid=0.0000025, amp2=max2, cen2=flight_times[1], wid2=0.0000025)
        fit_results = [(result.params['amp'].value, result.params['wid'].value,
                        result.params['cen'].value),
                       (result.params['amp'].value, result.params['wid'].value,
                        result.params['cen'].value)]
    usefull = result.success
        
    if axis is not None:
        axis.plot(values['x'], values['y'], 'k-')
        if len(flight_times) == 1:
            #ax.plot(X_values, result.init_fit+background, 'k--')
            axis.plot(values['x'], gaussian(values['x'], result.params['amp'].value,
                                            result.params['cen'].value,
                                            result.params['wid'].value) + background, 'r-')
        if len(flight_times) == 2:
            #ax.plot(X_values, result.init_fit, 'k--')
            axis.plot(values['x'], double_gaussian(values['x'], result.params['amp'].value,
                                                   result.params['cen'].value,
                                                   result.params['wid'].value,
                                                   result.params['amp2'].value,
                                                   result.params['cen2'].value,
                                                   result.params['wid2'].value)+background, 'r-')

        axis.axvline(values['x'][center-fit_width])
        axis.axvline(values['x'][center+fit_width])
        #axis.annotate(str(time), xy=(.05, .85), xycoords='axes fraction', fontsize=8)
        axis.annotate("Usefull: " + str(usefull), xy=(.05, .7),
                      xycoords='axes fraction', fontsize=8)
        #plt.show()
    return usefull, fit_results


def get_data(spectrum_number, cursor):
    """ Load data from spectrum number """
    try:
        data = pickle.load(open(str(spectrum_number) + '.p', 'rb'))
    except (IOError, EOFError):
        query = 'SELECT x*1000000, y FROM ' + XY_VALUES_TABLE
        query += ' where measurement = ' + str(spectrum_number)
        cursor.execute(query)
        data = np.array(cursor.fetchall())
        pickle.dump(data, open(str(spectrum_number) + '.p', 'wb'))
    try:
        query = 'select time, unix_timestamp(time), ' + NORMALISATION_FIELD + ' from '
        query += MEASUREMENT_TABLE + ' where id = "' + str(spectrum_number) + '"'
    except NameError: # No normalisation
        query = 'select time, unix_timestamp(time), 1 from ' + MEASUREMENT_TABLE
        query += ' where id = "' + str(spectrum_number) + '"'
    cursor.execute(query)
    spectrum_info = cursor.fetchone()
    return data, spectrum_info

def find_dateplot_info(spectrum_info, cursor):
    """ Find dateplot info for the spectrum """
    query = 'SELECT unix_timestamp(time), value FROM ' + DATEPLOT_TABLE
    query += ' where type = ' + str(DATEPLOT_TYPE) + ' and time < "'
    query += str(spectrum_info[0]) + '" order by time desc limit 1'
    cursor.execute(query)
    before_value = cursor.fetchone()
    time_before = spectrum_info[1] - before_value[0]
    assert time_before > 0
    before = {'value': before_value, 'time': time_before}

    query = 'SELECT unix_timestamp(time), value FROM ' + DATEPLOT_TABLE
    query += ' where type = ' + str(DATEPLOT_TYPE) + ' and time > "'
    query += str(spectrum_info[0]) + '" order by time limit 1'
    cursor.execute(query)
    after_value = cursor.fetchone()
    time_after = after_value[0] - spectrum_info[1]
    assert time_after > 0
    after = {'value': after_value, 'time': time_after}
    calculated_temp = (before['value'][1] * before['time'] +
                       after['value'][1] * after['time']) / (after['time'] + before['time'])
    return calculated_temp

def main(fit_info, spectrum_numbers):
    """ Main function """
    conn = mysql.connector.connect(host="servcinf-sql.fysik.dtu.dk", user="cinf_reader",
                                   passwd="cinf_reader", db="cinfdata")
    cursor = conn.cursor()

    dateplot_values = []
    timestamps = []

    for x_value in fit_info:
        fit_info[x_value]['peak_area'] = {}
        fit_info[x_value]['errors'] = {}
        for name in fit_info[x_value]['names']:
            fit_info[x_value]['peak_area'][name] = []
            fit_info[x_value]['errors'][name] = []

    pdf_file = PdfPages('multipage.pdf')
    for spectrum_number in spectrum_numbers:
        print(spectrum_number)
        data, spectrum_info = get_data(spectrum_number, cursor)
        calculated_temp = find_dateplot_info(spectrum_info, cursor)
        dateplot_values.append(calculated_temp)

        i = 0
        pdffig = plt.figure()
        for x in fit_info:
            i = i + 1
            axis = pdffig.add_subplot(2, 2, i)
            if i == 1:
                axis.text(0, 1.2, 'Spectrum id: ' + str(spectrum_number),
                          fontsize=12, transform=axis.transAxes)
                axis.text(0, 1.1, 'Sweeps: {0:.2e}'.format(spectrum_info[2]),
                          fontsize=12, transform=axis.transAxes)
            usefull, results = fit_peak(fit_info[x]['flighttime'], data, axis)

            for i in range(0, len(fit_info[x]['names'])):
                name = fit_info[x]['names'][i]
                area = math.sqrt(math.pi)*results[i][0] * math.sqrt(results[i][1])
                if usefull:
                    print(name)
                    fit_info[x]['peak_area'][name].append(area * 2500 / spectrum_info[2])
                    fit_info[x]['errors'][name].append(math.sqrt(area * 2500) /
                                                       spectrum_info[2])
                else:
                    fit_info[x]['peak_area'][name].append(None)
                    fit_info[x]['errors'][name].append(None)
                print(usefull)

        timestamps.append(spectrum_info[1])
        plt.savefig(pdf_file, format='pdf')
        plt.close()
    pdf_file.close()

    timestamps[:] = [t - timestamps[0] for t in timestamps]

    fig = plt.figure()
    axis = fig.add_subplot(1, 1, 1)

    for x in fit_info:
        for i in range(0, len(fit_info[x]['names'])):
            name = fit_info[x]['names'][i]
            try:
                axis.errorbar(timestamps, fit_info[x]['peak_area'][name], linestyle='-',
                              marker='o', label=fit_info[x]['names'][i],
                              yerr=fit_info[x]['errors'][name])
            except TypeError: # Cannot plot errorbars on plots with missing points
                axis.plot(timestamps, fit_info[x]['peak_area'][name],
                          linestyle='-', marker='o', label=str(x))

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
    FIT_INFO = {}
    FIT_INFO['M4'] = {}
    FIT_INFO['M4']['flighttime'] = [5.53]
    FIT_INFO['M4']['names'] = ['He']

    FIT_INFO['11.46'] = {}
    FIT_INFO['11.46']['flighttime'] = [11.455, 11.467]
    FIT_INFO['11.46']['names'] = ['11.46-low', '11.46-high']

    FIT_INFO['11.82'] = {}
    FIT_INFO['11.82']['flighttime'] = [11.81, 11.831]
    FIT_INFO['11.82']['names'] = ['11.82-low', '11.82-high']
    #Todo: Also include fit-information such as exact peak position

    SPECTRUM_NUMBERS = range(4160, 4165)
    
    main(FIT_INFO, SPECTRUM_NUMBERS)
