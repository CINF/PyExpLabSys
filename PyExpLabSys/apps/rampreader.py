from operator import itemgetter

class RampReader():
    def __init__(self, filename='temp_ramp.txt'):
        self.file = open(filename,'r')
        self.lines = self.file.readlines()
        self.file.close()

        self.remove_lines_and_comments()

        keys = []
        current_values = {}
        for line in self.lines:
            row = line.split(';')
            key = row[0].lower()
            if not key in keys:
                keys.append(key)
                current_values[key] = 0
        params = []
        params.append(current_values)

        i = 0
        for line in self.lines:
            i = i + 1
            row = line.split(';')
            param = row[0].lower()
            value = float(row[1])
            if param == 'time': #New time step, store the old values
                params.append(current_values.copy())
                current_values['time'] += value
            else:
                current_values[param] = value
        self.params = sorted(params, key=itemgetter('time'))

    def remove_lines_and_comments(self):
        #Mark empty lines and comments
        for i in range(0,len(self.lines)):
            if self.lines[i][0] in ['\n','#']:
                self.lines[i] = ''
            self.lines[i] = self.lines[i].strip() #Remove LF, CR and spaces from all lines

        #Remove all empty lines, including the ones just marked as empty
        for i in range(0,self.lines.count('')):
            self.lines.remove('')
        return True
        
    def get_values(self, time):
        pass



reader = RampReader()
print(reader.params)
