from __future__ import print_function
import matplotlib.pyplot as plt
import numpy as np
import scipy
try:
    import pymysql
except ImportError:
    import MySQLdb as pymysql
import pickle
import time
import math
from lmfit import Model
from lmfit import Parameters
from matplotlib.backends.backend_pdf import PdfPages

PEAK_FIT_WIDTH = 25
DATEPLOT_TABLE = 'dateplots_mgw'
#DATEPLOT_TABLE = 'dateplots_hall'
#DATEPLOT_TYPE = 166 # Hall
#DATEPLOT_TYPE = 273 # Bubbler
DATEPLOT_TYPE = 140 # TC in containment volume
#DATEPLOT_TYPE = 61 # Buffer
#DATEPLOT_TYPE = 141 # RTD
#DATEPLOT_TYPE = 217 #Containment volume
#DATEPLOT_TYPE = 270 #Capillary
#DATEPLOT_TYPE = 271 #DBT bubbler valve

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
    if len(values['y_fit']) == 0:
        values['x_fit'] = values['x']
        values['y_fit'] = values['y'] - background

    if len(flight_times) == 1:
        gmod = Model(gaussian)
        parms = gmod.make_params(amp=max(values['y_fit']), cen=flight_times[0], wid=0.0000025)
        parms['amp'].min = 0
        parms['amp'].max = 2 * max(values['y_fit'])
        parms['wid'].min = 0.0000015
        parms['wid'].max = 0.0000195
        result = gmod.fit(values['y_fit'], x=values['x_fit'], amp=parms['amp'], cen=parms['cen'], wid=parms['wid'])
        #result = gmod.fit(values['y_fit'], x=values['x_fit'], amp=max(values['y_fit']),
        #                  cen=flight_times[0], wid=0.0000025)
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
        try:
            axis.axvline(values['x'][center-fit_width])
            axis.axvline(values['x'][center+fit_width])
        except:
            pass
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

def main(fit_info, spectrum_numbers, exclude_numbers):
    """ Main function """
    try:
        conn = pymysql.connect(host="servcinf-sql.fysik.dtu.dk", user="cinf_reader",
                                   passwd="cinf_reader", db="cinfdata")
        cursor = conn.cursor()
    except pymysql.OperationalError:
        conn = pymysql.connect(host="localhost", user="cinf_reader", passwd="cinf_reader", db="cinfdata", port=999)
        cursor = conn.cursor()
        
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
        if spectrum_number in exclude_numbers: #NEW
            print('SKIPPING', spectrum_number)
            continue
        print(spectrum_number)
        data, spectrum_info = get_data(spectrum_number, cursor)
        calculated_temp = find_dateplot_info(spectrum_info, cursor)
        dateplot_values.append(calculated_temp)

        j = 0
        pdffig = plt.figure()
        for x in fit_info:
            j = j + 1
            axis = pdffig.add_subplot(4, 4, j)
            if j == 1:
                axis.text(0, 1.2, 'Spectrum id: ' + str(spectrum_number),
                          fontsize=12, transform=axis.transAxes)
                axis.text(0, 1.1, 'Sweeps: {0:.2e}'.format(spectrum_info[2]),
                          fontsize=12, transform=axis.transAxes)
            usefull, results = fit_peak(fit_info[x]['flighttime'], data, axis)

            for i in range(0, len(fit_info[x]['names'])):
                name = fit_info[x]['names'][i]
                try:
                    area = math.sqrt(math.pi)*results[i][0] * math.sqrt(results[i][1])
                except ValueError:
                    area = 0
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

    export_data = {}
    export_data['timestamp'] = timestamps
    for x in fit_info:
        for i in range(0, len(fit_info[x]['names'])): ## Itereate over number of peaks
            name = fit_info[x]['names'][i]
            export_data[name] = fit_info[x]['peak_area'][name]
            try:
                axis.errorbar(timestamps, fit_info[x]['peak_area'][name], linestyle='-',
                              marker='o', label=fit_info[x]['names'][i],
                              yerr=fit_info[x]['errors'][name])
            except TypeError: # Cannot plot errorbars on plots with missing points
                axis.plot(timestamps, fit_info[x]['peak_area'][name],
                          linestyle='-', marker='o', label=str(x))
    export_string = ''
    for name in export_data.keys():
        export_string += name + ' '
    export_string += '\n'
    for j in range(0, len(export_data[name])):
        for name in export_data.keys():
                export_string += str(export_data[name][j]) + ' '
        export_string += '\n'
    print(export_string)
    export_file = open('export.txt', 'w')
    export_file.write(export_string)
    export_file.close()
    axis2 = axis.twinx()
    axis2.plot(timestamps, dateplot_values, 'k-', label='test')
    axis.tick_params(direction='in', length=2, width=1, colors='k',labelsize=28, axis='both', pad=2)
    axis2.tick_params(direction='in', length=2, width=1, colors='k',labelsize=28, axis='both', pad=2)
    axis.set_ylabel('Integraged peak area', fontsize=28)
    axis2.set_ylabel('Temperature', fontsize=25)
    axis.set_xlabel('Time / s', fontsize=25)
    axis.set_yscale('log')

    axis.legend(loc='upper left', fontsize=20)

    plt.show()

    #print('----')
    #print(dateplot_values)
    #print('----')
    #print(peak_areas)
    #print('----')


if __name__ == '__main__':

    FIT_INFO = {}
    FIT_INFO['M2'] = {}
    FIT_INFO['M2']['flighttime'] = [3.8]
    FIT_INFO['M2']['names'] = ['H2']    
    
    #FIT_INFO = {}
    FIT_INFO['M4'] = {}
    FIT_INFO['M4']['flighttime'] = [5.52]
    FIT_INFO['M4']['names'] = ['He']
    
    #FIT_INFO['M17']= {}
    #FIT_INFO['M17']['flighttime'] = [11.81]
    #FIT_INFO['M17']['names'] = ['NH3']    
    
    #FIT_INFO['M159'] = {}
    #FIT_INFO['M159']['flighttime'] = [36.94]
    #FIT_INFO['M159']['names'] = ['MAI']
 
    #FIT_INFO['M127'] = {}
    #FIT_INFO['M127']['flighttime'] = [32.95]
    #FIT_INFO['M127']['names'] = ['I']
    
    #FIT_INFO['M142'] = {}
    #FIT_INFO['M142']['flighttime'] = [34.87]
    #FIT_INFO['M142']['names'] = ['M142']

    #FIT_INFO['M268'] = {}
    #FIT_INFO['M268']['flighttime'] = [48.05]
    #FIT_INFO['M268']['names'] = ['M268']
    
    #FIT_INFO['M254'] = {}
    #FIT_INFO['M254']['flighttime'] = [46.76]
    #FIT_INFO['M254']['names'] = ['I2']
    
    #FIT_INFO['M18'] = {}
    #FIT_INFO['M18']['flighttime'] = [12.16]
    #FIT_INFO['M18']['names'] = ['H18']    
    
    #FIT_INFO['M28'] = {}
    #FIT_INFO['M28']['flighttime'] = [15.26]
    #FIT_INFO['M28']['names'] = ['H28']    
 
    FIT_INFO['M34'] = {}
    FIT_INFO['M34']['flighttime'] = [16.86]
    FIT_INFO['M34']['names'] = ['H2S']
    
    #FIT_INFO['M149'] = {}
    #FIT_INFO['M149']['flighttime'] = [35.74]
    #FIT_INFO['M149']['names'] = ['M149']    
    
    FIT_INFO['BiPhe'] = {}
    FIT_INFO['BiPhe']['flighttime'] = [36.345]
    FIT_INFO['BiPhe']['names'] = ['BiPhe']
    
    #FIT_INFO['Background'] = {}
    #FIT_INFO['Background']['flighttime'] = [36.6]
    #FIT_INFO['Background']['names'] = ['Background']
    
    
    
    FIT_INFO['DBT'] = {}
    FIT_INFO['DBT']['flighttime'] = [39.75]
    FIT_INFO['DBT']['names'] = ['DBT']
    #
    #FIT_INFO['M127'] = {}
    #FIT_INFO['M127']['flighttime'] = [32.95, 32.98]
    #FIT_INFO['M127']['names'] = ['I-low', 'I-high']

    #FIT_INFO['M85'] = {}
    #FIT_INFO['M85']['flighttime'] = [26.89, 26.91]
    #FIT_INFO['M85']['names'] = ['M85-low', 'M85-high']
  
    #FIT_INFO['M85-high'] = {}
    #FIT_INFO['M85-high']['flighttime'] = [26.91]
    #FIT_INFO['M85-high']['names'] = ['M85-high']
    
    #FIT_INFO['M85-low'] = {}
    #FIT_INFO['M85-low']['flighttime'] = [26.89]
    #FIT_INFO['M85-low']['names'] = ['M85-low']
    
        
    


    """
    FIT_INFO['21.97'] = {}
    FIT_INFO['21.97']['flighttime'] = [21.97]
    FIT_INFO['21.97']['names'] = ['Oil']

    FIT_INFO['24.57'] = {}
    FIT_INFO['24.57']['flighttime'] = [24.57]
    FIT_INFO['24.57']['names'] = ['Oil II'] 
    """
    #FIT_INFO['11.82'] = {}
    #FIT_INFO['11.82']['flighttime'] = [11.81, 11.831]
    #FIT_INFO['11.82']['names'] = ['11.82-low', '11.82-high']
    #Todo: Also include fit-information such as exact peak position
    #SPECTRUM_NUMBERS = range(28263, 29762)
    SPECTRUM_NUMBERS = range(28263, 28475)

    #SPECTRUM_NUMBERS = range(9532, 10440)
    EXCLUDE_NUMBERS = set([9454, 9458, 9464, 9465, 9478, 9487, 9505, 9905, 9940, 9955, 9971, 9991, 9994, 10007, 10078, 10106, 10139, 10142, 10188, 10203, 10213, 10216, 10324, 10442, 10444, 10463, 10470, 14118])
    # 10188 10212 
    
    main(FIT_INFO, SPECTRUM_NUMBERS, EXCLUDE_NUMBERS)
