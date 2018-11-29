from cinfdata import Cinfdata
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from scipy.stats import linregress
from scipy.integrate import simps

"""
Author: Jakob Ejler Sørensen
"""


def get_range(X, time):
    A = np.where(X > time[0])[0][0]
    B = np.where(X < time[1])[0][-1]
    return np.arange(A, B)

def time2temp(data):
    time = data[:,0]
    temp = data[:,1]
    # Cycle through points and average groups
    times = np.array([])
    temps = np.array([])
    stds = np.array([])
    for i in range(len(time)):
        if i == 0:
            first = i
            value = temp[i]
            continue
        if temp[i] - value != 0:
            # Collect oversampling of temperature in a single point:
            # Extract region
            region = np.arange(first, i)
            times = np.append(times, time[region].mean())
            stds = np.append(stds, time[region].std())
            temps = np.append(temps, value)
            # Reset counters
            first = i
            value = temp[i]
    region = np.arange(first, i)
    times = np.append(times, time[region].mean())
    stds = np.append(stds, time[region].std())
    temps = np.append(temps, value)
    # Create interpolate function
    interpolate = interp1d(times, temps, kind='linear')#, bounds_error=False, fill_value='extrapolate')
    return interpolate


def import_data(ID, setup='omicron'):
    db = Cinfdata(setup, use_caching=True)
    data = db.get_data(ID)
    try:
        data[:,0] = data[:,0]/1000
    except:
        meta = db.get_metadata(ID)
        print('"{}" data for ID {} is empty and set to "None"'.format(meta['mass_label'], ID))
        data = None
    return data

#ALT_INFO = ['Analysis pressure', 'Preparation pressure',
#            'Sample temperature', 'Setpoint temperature',
#            'Voltage setpoint', 'Voltage monitor',
#            'Current setpoint', 'Current monitor']

class TPD_data(object):
    """Imports a TPD data set from Omicron into a TPD class to implement
different practical functions for data treatment"""

    def __init__(self, timestamp, caching=True):
        """Save all data in 'DATA' dict object"""

        # Connect to database
        db = Cinfdata('omicron',
                    use_caching=caching,
                    grouping_column='time',
                    )
        # Get data in unit seconds
        group_data = db.get_data_group(timestamp, scaling_factors=(1E-3, None))
        group_meta = db.get_metadata_group(timestamp)
        # Get a list of labels and group data
        self.name = group_meta[list(group_meta.keys())[0]]['Comment']
        self.labels = [group_meta[key]['mass_label'] for key in group_data.keys()]
        self.data = {group_meta[key]['mass_label']: group_data[key] for key in group_data.keys()}
        print('Loaded data from Experiment: "{}"'.format(self.name))


    def isolate_experiments(self, set_label=None):
        """
1) Isolate regions of heating ramps
2) Organize into returnable data
3) Convert time to temperature
    - intentionally oversample the temperature
    - collect groups into points of average/std
    - interpolate points to correlate arbitrary time with a temperature
"""

        # 1) Find regions of heating ramps
        if set_label is None:
            for i in self.labels:
                if 'setpoint' in i.lower().split() and 'temperature' in i.lower().split():
                    set_label = i
                    break
        if set_label is None:
            print('Label is not found automatically. Specify temperature ramp label.')
            raise ValueError()
        if len(self.data[set_label]) == 0:
            raise ValueError('No heat ramps detected')
        marker_start, marker_end = 0, 0
        counter = 0
        regions = []
        for i in self.data[set_label][:,0]:
            if counter == 0:
                last = i
                marker_start = counter
                counter += 1
                continue

            # Main check
            if i - last > 15: # difference of more than 15 seconds
                marker_end = counter
                region = np.arange(marker_start, marker_end)
                regions.append(region)
                marker_start = counter

            # End of loop
            last = i
            counter += 1
        region = np.arange(marker_start, counter)
        regions.append(region)
        number_of_regions = len(regions)

        # 2) Organize into returnable data
        temp_label = 'Sample temperature'
        if not temp_label in self.labels:
            for i in self.labels:
                if 'sample' in i.lower() and 'temperature' in i.lower():
                    temp_label = i
                    print('Temperature label deviating from default found: "{}"'.format(temp_label))
                    break
        interpolate = time2temp(self.data[temp_label])
        exp = {}
        for i in range(number_of_regions):
            exp[i] = {}
            region = regions[i]
            time_ref = self.data[set_label][:,0][region]
            for label in self.labels:
                # skip if empty
                if self.data[label] == None:
                    continue
                exp[i][label] = {}
                local_range = get_range(self.data[label][:, 0], [time_ref[0]-3, time_ref[-1]+3])
                for x in [0, 1]:
                    exp[i][label][x] = self.data[label][:, x][local_range]

            # 3) Add temperature axis to each data set (except "Temperature")
            for label in self.labels:
                # skip if empty
                if self.data[label] == None:
                    continue
                #print(i, label)
                exp[i][label][2] = interpolate(exp[i][label][0])
            slope, intercept, rvalue, pvalue, std_err = linregress(exp[i][temp_label][0], exp[i][temp_label][1])
            exp[i]['Slope'] = slope*exp[i][temp_label][0] + intercept
        return exp

def get_total_signal(exp, ID):
    """ Integrate time based QMS signal from 'isolate_experiments()' 
Resembles a lot"""

    # For every experiment, add integrated signal as 'COVERAGE'
    coverage = np.zeros(len(exp.viewkeys()))
    for i in exp.viewkeys():
        ranges = []
        x = exp[i][ID][0]
        y = exp[i][ID][1]
        N = len(x)
        indice = np.arange(10)
        indice = np.append(indice, range(N-10, N))
        slope, intercept, rvalue, pvalue, std_err = linregress(x[indice], y[indice])
        baseline = intercept + slope*x
        coverage[i] = simps(y - baseline, x=x) 
    return coverage



def get_doseage(data, times):
    """ Integrate doses """

    # Initialize variables and ranges
    ranges = []
    for deltat in times:
        ranges.append(get_range(data[:,0], deltat))
    doses = np.zeros(len(ranges))

    # Loop to subtract background and integrate doseages
    i = 0
    for r in ranges:
        x = data[:,0][r]
        y = data[:,1][r]
        N = len(x)
        indice = np.arange(10)
        indice = np.append(indice, range(N-10, N))
        slope, intercept, rvalue, pvalue, std_err = linregress(x[indice], y[indice])
        baseline = intercept + slope*x
        doses[i] = simps(y - baseline, x=x)
        i += 1
    return doses



def tick_function(T):
    """ Dummy function for 'ADD_SCALE_KELVIN' """

    K = T + 273.15
    return ["%d" % z for z in K]



def add_scale_Kelvin(ax, axis='x'):
    """ Convert a Celcius axis to Kelvin and coplot on opposite axis """

    if axis not in ['x', 'y']:
        raise ValueError('Choose \'x\' or \'y\' as AXIS')
    if axis == 'x':
        ax_twin = ax.twiny()
        ax_twin.set_xlim(ax.get_xlim())
        new_ticks = ax.get_xticks()
    elif axis == 'y':
        ax_twin = ax.twinx()
        ax_twin.set_ylim(ax.get_ylim())
        new_ticks = ax.get_yticks()
    new_start = 100 - 273.15
    new_ticklocations = np.arange(len(new_ticks)-1)*np.diff(new_ticks) + new_start
    if axis == 'x':
        ax_twin.set_xticks(new_ticklocations)
        ax_twin.set_xticklabels(tick_function(new_ticklocations))
        ax_twin.set_xlabel('Temperature (K)')
    elif axis == 'y':
        ax_twin.set_yticks(new_ticklocations)
        ax_twin.set_yticklabels(tick_function(new_ticklocations))
        ax_twin.set_ylabel('Temperature (K)')



def Veff(H, r = 0.5):
    """Effort to estimate the volume between sniffer and sample"""
    return r * H**2 + r**2 * H + 1./3 * H**3



def generate_standard_plots(exp, coverage=None, doses=None, selection=[]):
    """ Generate standard plots for a single TPD experiment. """

    # Check if selection has been given
    if len(selection) < 1:
        selection = exp.viewkeys()

    GUIDE_LINES = (np.arange(10)+1) * 100
    fig, ax = {}, {}    
    # Plot general data overview plot for each sub-TPD
    for i in selection:
        fig_id = 'overview TPD {}'.format(i)
        fig[fig_id] = plt.figure(fig_id)

        # Plot actual TPD result
        ax[i] = {}
        ax[i][1] = fig[fig_id].add_subplot(221)
        data = exp[i]['M30']
        ax[i][1].plot(data[2], data[1], 'r-')
        ax[i][1].set_xlabel('Temperature (C)')
        ax[i][1].set_ylabel('SEM current (A)')
        add_scale_Kelvin(ax[i][1])

        # Plot raw signal vs time
        ax[i][2] = fig[fig_id].add_subplot(222)
        ax[i][2].plot(data[0] - data[0][0], data[1], 'ro-')
        ax[i][2].set_xlabel('Time (s)')
        ax[i][2].set_ylabel('SEM current (A)')
        if not coverage is None and not doses is None:
            ax[i][2].text(0.5, 0.85, 'Dose:        {:.3} mbar s\nCoverage: {:.3} C'.format(doses[i], coverage[i]), transform=ax[i][2].transAxes)

        # Plot temperature vs time
        ax_id = 'temperature {}'.format(i)
        ax[i][3] = fig[fig_id].add_subplot(223)
        data = exp[i]['Sample temperature']
        slope = exp[i]['Slope']
        ax[i][3].plot(data[0] - data[0][0], data[1], 'b-')
        ax[i][3].plot(data[0] - data[0][0], slope, 'k-')
        value_of_slope = (slope[-1]- slope[0])/(data[0][-1]-data[0][0])
        ax[i][3].text(.05, 0.7, 'Heat rate: {:.3} K/s'.format(value_of_slope), transform=ax[i][3].transAxes)
        ax[i][3].set_xlabel('Time (s)')
        ax[i][3].set_ylabel('Temperature (C)')
        add_scale_Kelvin(ax[i][3], axis='y')

        # Plot difference in temperature and slope vs time
        ax[i][4] = fig[fig_id].add_subplot(224)
        ax[i][4].axhline(y=0, linestyle='solid', color='k')
        for j in [-1, 1]:
            ax[i][4].axhline(y=j, linestyle='dashed', color='k')
        ax[i][4].plot(data[0] - data[0][0], data[1] - slope, 'b-')
        ax[i][4].set_xlabel('Time (s)')
        ax[i][4].set_ylabel('Temp$_{meas}$ - Temp$_{avg}$')

        # Plot power supply data
        fig_id = 'Filament data {}'.format(i)
        fig[fig_id] = plt.figure(fig_id)
        ax[i][5] = fig[fig_id].add_subplot(121)
        data = exp[i]['Voltage monitor']
        ax[i][5].plot(data[0] - data[0][0], data[1], 'k-')
        ax[i][5].set_xlabel('Time (s)')
        ax[i][5].set_ylabel('Voltage (V)')
        ax[i][5].set_ylim([0, 6.5])
        ax[i][5].arrow(.7, .4, 0.05, 0, color='m', transform=ax[i][5].transAxes)
        ax[i][5].text(.7, .4, 'Current ', color='m', verticalalignment='center', horizontalalignment='right', transform=ax[i][5].transAxes)
        ax[i][5].arrow(.55, .3, -0.05, 0, color='k', transform=ax[i][5].transAxes)
        ax[i][5].text(.55, .3, ' Voltage', color='k', verticalalignment='center', horizontalalignment='left', transform=ax[i][5].transAxes)
        ax_twinx = ax[i][5].twinx()
        
        data = exp[i]['Current monitor']
        ax_twinx.plot(data[0] - data[0][0], data[1], 'm-')
        ax_twinx.set_ylim([0, 6.0])
        ax_twinx.set_ylabel('Current (A)')

        # Plot PID data
        ax[i][6] = fig[fig_id].add_subplot(122)
        data = exp[i]['P error']
        x = data[0] - data[0][0]
        y = data[1]
        ax[i][6].plot(x[25:], y[25:], 'k-') # Hardcoded index range due to earlier extended experiment region
        ax[i][6].set_xlabel('Time (s)')
        ax[i][6].set_ylabel('P error')
        ax_twinx = ax[i][6].twinx()
        
        data = exp[i]['I error']
        x = data[0] - data[0][0]
        y = data[1]
        ax_twinx.plot(x[25:], y[25:], 'm-') # Hardcoded index range due to earlier extended experiment region
        ax_twinx.set_ylabel('I error')

        # Plot guiding lines
        XLIM = [0, data[0][-1]-data[0][0]]
        for j in [2, 3, 4, 5, 6]:
            print(i,j)
            axis = ax[i][j]
            for X in GUIDE_LINES:
                axis.axvline(x=X, linestyle='-.', color='k', alpha=0.3)
            axis.set_xlim(XLIM)

    # Plot main result
    fig_id = 'Result'
    fig[fig_id] = plt.figure(fig_id)
    ax_id = 'Result'
    ax[ax_id] = fig[fig_id].add_subplot(111)
    for i in selection:
        data = exp[i]['M30']
        ax[ax_id].plot(data[2], data[1])
    ax[ax_id].set_xlabel('Temperature (C)')
    ax[ax_id].set_ylabel('SEM current (A)')
    ax[ax_id].text(0.05, 0.90, 'm/z = 30', color='k')
    add_scale_Kelvin(ax[ax_id])

    if not coverage is None and not doses is None:
        # Plot uptake curve
        fig_id = 'Uptake curve'
        fig[fig_id] = plt.figure(fig_id)
        ax_id = 'Uptake curve'
        ax[ax_id] = fig[fig_id].add_subplot(111)
        ax[ax_id].plot(doses/1.33e-6, coverage, 'ko')
        ax[ax_id].set_xlabel('Doseage (1.33e-6 mbar s)')
        ax[ax_id].set_ylabel('Coverage (C)')
        x1, x2 = ax[ax_id].get_xlim()
        ax[ax_id].set_xlim([0, x2])

    # Show plots
    plt.show()

def peak2energy(Edes, Tpeak, beta=2, nu=1e13, ret='optimum'):
    """Convert a TPD peak temperature 'Tpeak' to a desorption energy 'Edes'
    Following equation (7.14) for first-order desorption in 'Concepts of
    Modern Catalysis and Kinetics', Chorkendorff, Niemantsverdriet, 2nd edition.

    Inputs:
        Edes (float): desorption energy [kJ/mol]
        Tpeak (float): peak temperature [K]
        beta (float, 2): heat rate [K/s]
        nu (float, 1e13): pre-exponential factor [1/s]
        ret (string, 'graph'): return type of function. Options are 'graph' or 'number'.
                'graph': returns a plot to determine Edes
                'number': returns difference between input and output (absolute)
                'optimum': returns optimal desorption energy

    Output:
        if ret='optimum': return best fit (float)
        if ret='graph': open a matplotlib plot (figure)
        if ret='number': return the absolute difference between input and output
    """

    kB = 1.38e-23 # Boltzmann constant
    NA = 6.022e23 # Avogadros number
    def rec_fun(E):
        """Equation (7.14)"""
        return kB*Tpeak * np.log( kB*Tpeak**2*nu/E/1000*NA/beta ) /1000*NA

    if ret == 'number':
        # Return deviation by guess
        return abs(rec_fun(Edes)-Edes)

    elif ret == 'optimum':
        # Use scipy.optimize to find Edes
        from scipy.optimize import minimize
        _ret = minimize(peak2energy, [Edes], args=(Tpeak, beta, nu, 'number'), bounds=[(1, 100)])
        print(_ret)
        return _ret.x[0]

    elif ret == 'graph':
        # Solve equation graphically
        interval = [Edes-20, Edes+21]
        if interval[0] <= 0:
            interval[0] = 0.1
        if interval[1] >= 200:
            interval[1] = 200
        x = np.arange(*interval)
        y = rec_fun(x)
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.plot(x, y, label='Edes(Edes)')
        ax.plot(x, x, label='Edes')
        ax.set_xlabel('Edes')
        plt.legend()
        return fig, ax

    return 'RET option not chosen correctly'


if __name__ == '__main__':
    data = TPD_data('2018-10-19 10:10:08', caching=False)
    exp = data.isolate_experiments()

    colors = ['k', 'r', 'g', 'b', 'm', 'y', 'c']

    # Plot experiment(s)
    fig = plt.figure(1)
    ax = fig.add_subplot(111)
    for i in exp.keys():
        dat = exp[i]['M30']
        ax.plot(dat[2], dat[1]/1e-12, marker='o', color=colors[i])
    ax.set_xlabel('Temperature (Celcius)')
    ax.set_ylabel('SEM current (pA)')
    add_scale_Kelvin(ax)

    plt.show()
