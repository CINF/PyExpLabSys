import matplotlib.pyplot as plt
import numpy as np
from operator import itemgetter

class RampReader():
    def __init__(self, filename='temp_ramp.txt'):
        file = open(filename, 'r')
        lines = file.readlines()
        file.close()

        lines = self.remove_lines_and_comments(lines)

        keys = []
        current_values = {}
        for line in lines:
            row = line.split(';')
            key = row[0].lower()
            if not key in keys:
                keys.append(key)
                current_values[key] = (0, False)
        params = []
        params.append(current_values)

        for line in lines:
            row = line.split(';')
            param = row[0].lower()
            value = float(row[1])
            try:
                ramp = row[2].lower() == 'ramp'
            except IndexError:
                ramp = False
            if param == 'time': #New time step, store the old values
                params.append(current_values.copy())
                new_time = current_values['time'][0] + value
                current_values['time'] = (new_time, False)
            else:
                current_values[param] = (value, ramp)
        # Sort according to the time key
        self.params = sorted(params, key=itemgetter('time'))
        print self.params


    def remove_lines_and_comments(self, lines):
        """ Remove all empty lines and comments from file """

        #Mark empty lines and comments
        for i in range(0, len(lines)):
            if lines[i][0] in ['\n','#']:
                lines[i] = ''
            lines[i] = lines[i].strip() #Remove LF, CR and spaces from all lines

        #Remove all empty lines, including the ones just marked as empty
        for i in range(0, lines.count('')):
            lines.remove('')
        return lines


    def get_value(self, time, key):
        old_param = self.params[0]
        for param in self.params:
            if param['time'][0] >= time:
                if param[key][1]:
                    dt1 = time - old_param['time'][0]
                    dt2 = param['time'][0] - time
                    time_span = ((param['time'][0] - time) + (time - old_param['time'][0]))
                    return (param[key][0] * dt1 + old_param[key][0] * dt2) / time_span
                else:
                    return old_param[key][0]
            else:
                old_param = param

    def plot_file(self):
        time_range = np.arange(0, self.params[-1]['time'][0], 0.1)
        plots = {}
        keys = self.params[0].keys()
        for key in keys:
            plots[key] = []

        for plot_time in time_range:
            for key in self.params[0].keys():
                plots[key].append(self.get_value(plot_time, key))

        keys.remove('time')
        keys.remove('temp')
        fig = plt.figure()
        axis = fig.add_subplot(1, 1, 1)
        axis2 = axis.twinx()
        
        plot_lines = axis2.plot(time_range, plots['temp'], linestyle='-', label = 'Temp', color='k')
        for key in keys:
            plot_lines += axis.plot(time_range, plots[key], linestyle='-', label=key)
        
        labels = [l.get_label() for l in plot_lines]
        axis.legend(plot_lines, labels)
        
        axis.set_ylabel('Value')
        #axis2.set_ylabel('Temperature')
        axis.set_xlabel('Time')
        #axis.legend(loc='upper left')
        plt.show()



reader = RampReader()
print('----')
print(reader.plot_file())
