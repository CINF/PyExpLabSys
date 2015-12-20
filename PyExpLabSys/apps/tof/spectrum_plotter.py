import sys
import matplotlib.pyplot as plt
import numpy as np
import mysql.connector
from scipy import optimize
from scipy import interpolate
import pickle
import math
import time
from lmfit import Model
from matplotlib.backends.backend_pdf import PdfPages


PEAK_FIT_WIDTH = 25
DATEPLOT_TABLE = 'dateplots_mgw'
DATEPLOT_TYPE = 273
MEASUREMENT_TABLE = 'measurements_tof'
XY_VALUES_TABLE= 'xy_values_tof'
NORMALISATION_FIELD = 'tof_iterations'

def gaussian(x, amp, cen, wid):
    return amp * math.e ** (-1 * ((x - cen) ** 2) / wid)
    
def double_gaussian(x, amp, cen, wid, amp2, cen2):
    peak1 = gaussian(x, amp, cen, wid)
    peak2 = gaussian(x, amp2, cen2, wid)
    return peak1 + peak2


def fit_peak_lm(flight_times, data, ax=None):
    time = np.mean(flight_times)
    center = np.where(Data[:,0] > time)[0][0]
    Start = center - 125 #Display range
    End = center + 125
    X_values = Data[Start:End,0]
    Y_values = Data[Start:End,1]
    center = np.where(Y_values == max(Y_values))[0][0]

    background = np.mean(Y_values[center-3*PEAK_FIT_WIDTH:center-2*PEAK_FIT_WIDTH])
    print('Background: ' + str(background))

    fit_width = PEAK_FIT_WIDTH + PEAK_FIT_WIDTH * (len(flight_times)-1) * 0.5
    #Fitting range
    x_values = X_values[center-fit_width:center+fit_width]
    y_values = Y_values[center-fit_width:center+fit_width]

    if len(flight_times) == 1:
        gmod = Model(gaussian)
        result = gmod.fit(Y_values, x=X_values, amp=max(Y_values),
                          cen=flight_times[0], wid=0.000002)

    if len(flight_times) == 2:
        center1 = np.where(Data[:,0] > flight_times[0])[0][0]
        max1 = max(Data[center1-10:center1+10, 1])

        center2 = np.where(Data[:,0] > flight_times[1])[0][0]
        max2 = max(Data[center2-10:center2+10, 1])
    
        gmod = Model(double_gaussian)
        result = gmod.fit(Y_values, x=X_values, amp=max1, cen=flight_times[0],
                          amp2=max2, cen2=flight_times[1], wid=0.000002)


    #usefull = (p1[0] > 1.5) and (p1[1] < 1e-3) and (result.success) # Only use the values if fit succeeded and peak has decent height
    usefull = result.success
    
    amp = result.params['amp'].value
    wid = result.params['wid'].value
    cen = result.params['cen'].value
    if len(flight_times) == 2:
        amp2 = result.params['amp2'].value
        cen2 = result.params['cen2'].value

    p1 = [amp, wid, 0]
    area_fit = math.sqrt(math.pi)*amp * math.sqrt(wid)

    area_count = np.sum(Y_values) - background*len(Y_values)
    if ax is not None:
        ax.plot(X_values, Y_values, 'k-')
        if len(flight_times) == 1:
            ax.plot(X_values, gaussian(X_values, amp, cen, wid)+background, 'r-')
        if len(flight_times) == 2:
            ax.plot(X_values, double_gaussian(X_values, amp, cen, amp2, cen2, wid)+background, 'r-')

        ax.axvline(X_values[center-fit_width])
        ax.axvline(X_values[center+fit_width])
        ax.annotate(str(time), xy=(.05,.85), xycoords='axes fraction',fontsize=8)
        ax.annotate("Fit Area: {0:.0f}".format(area_fit*2500), xy=(.05,.8), xycoords='axes fraction',fontsize=8)
        ax.annotate("Count Area: {0:.0f}".format(area_count), xy=(.05,.75), xycoords='axes fraction',fontsize=8)
        ax.annotate("Usefull: " + str(usefull), xy=(.05,.7), xycoords='axes fraction',fontsize=8)
        #plt.show()
    return usefull, p1, 0


db = mysql.connector.connect(host="servcinf-sql.fysik.dtu.dk", user="cinf_reader",passwd = "cinf_reader", db = "cinfdata")
cursor = db.cursor()

#spectrum_numbers = range(4160, 4255)
spectrum_numbers = range(4160, 4161)

x_values = {}
x_values['M4'] = {}
x_values['M4']['flighttime'] = [5.53]
x_values['M4']['names'] = ['He']

x_values['11.46'] = {}
x_values['11.46']['flighttime'] = [11.455, 11.468]
x_values['11.46']['names'] = ['11.46-low', '11.46-high']

x_values['11.82'] = {}
x_values['11.82']['flighttime'] = [11.81, 11.83]
x_values['11.82']['names'] = ['11.82-low', '11.82-high']
#Todo: Also include fit-information such as exact peak position

#x_values = [5.53, 11.82, 39.81]
#x_values = [39.81]

dateplot_values = []
timestamps = []

for x in x_values:
    x_values[x]['peak_area'] = []
    x_values[x]['errors'] = []

pp = PdfPages('multipage.pdf')
for spectrum_number in spectrum_numbers:
    print(spectrum_number)
    t = time.time()
    try:
        Data = pickle.load(open(str(spectrum_number) + '.p', 'rb'), encoding='latin1')
    except (IOError, EOFError):
        cursor.execute('SELECT x*1000000,y FROM ' + XY_VALUES_TABLE +  ' where measurement = ' + str(spectrum_number))
        Data = np.array(cursor.fetchall())
        pickle.dump(Data, open(str(spectrum_number) + '.p', 'wb'))
    print(time.time() - t)

    try:
        NORMALISATION_FIELD
        query = 'select time, unix_timestamp(time), ' + NORMALISATION_FIELD + ' from ' + MEASUREMENT_TABLE + ' where id = "' + str(spectrum_number) + '"'
    except NameError: # No normalisation
        query = 'select time, unix_timestamp(time), 1 from ' + MEASUREMENT_TABLE + ' where id = "' + str(spectrum_number) + '"'
    cursor.execute(query)
    spectrum_info = cursor.fetchone()

    query = 'SELECT unix_timestamp(time), value FROM ' + DATEPLOT_TABLE + ' where type = ' + str(DATEPLOT_TYPE) + ' and time < "' + str(spectrum_info[0]) + '" order by time desc limit 1';
    cursor.execute(query)
    before_value = cursor.fetchone()
    time_before = spectrum_info[1] - before_value[0]
    assert(time_before > 0)

    query = 'SELECT unix_timestamp(time), value FROM ' + DATEPLOT_TABLE + ' where type = ' + str(DATEPLOT_TYPE) + ' and time > "' + str(spectrum_info[0]) + '" order by time limit 1';
    cursor.execute(query)
    after_value = cursor.fetchone()
    time_after = after_value[0] - spectrum_info[1]
    assert(time_before > 0)

    calculated_temp = (before_value[1] * time_before + after_value[1] * time_after) / (time_after + time_before)
    dateplot_values.append(calculated_temp)

    i = 0
    pdffig = plt.figure()    
    for x in x_values:
        i = i + 1
        axis = pdffig.add_subplot(2,2,i)
        if i == 1:
            axis.text(0,1.2,'Spectrum id: ' + str(spectrum_number),fontsize=12,transform = axis.transAxes)
            axis.text(0,1.1,'Sweeps: {0:.2e}'.format(spectrum_info[2]),fontsize=12,transform = axis.transAxes)
        usefull, p1, count = fit_peak_lm(x_values[x]['flighttime'],  Data, axis)
        area = math.sqrt(math.pi)*p1[0] * math.sqrt(p1[1])
        if usefull:
            x_values[x]['peak_area'].append(area * 2500 / spectrum_info[2])
            x_values[x]['errors'].append(math.sqrt(area * 2500) / spectrum_info[2]) 
        else:
            x_values[x]['peak_area'].append(None)
            x_values[x]['errors'].append(None) 
        print(usefull)
   
    timestamps.append(spectrum_info[1])
    plt.savefig(pp, format='pdf')                                                                      
    plt.close()
pp.close()

timestamps[:] = [t - timestamps[0] for t in timestamps]

fig = plt.figure()
axis = fig.add_subplot(1, 1, 1)

for x in x_values:
    try:
        axis.errorbar(timestamps, x_values[x]['peak_area'], linestyle='-', marker='o', label=x, yerr=x_values[x]['errors'])
    except TypeError: # Cannot plot errorbars on plots with missing points
        axis.plot(timestamps, x_values[x]['peak_area'], linestyle='-', marker='o', label=str(x))

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
