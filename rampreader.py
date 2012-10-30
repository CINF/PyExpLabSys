f = open('temp_ramp.txt','r')

TIME = 0
TEMP = 1

keys = ['time','temp']
#init_vals = zip(keys,vals)

params = []
#params.append(dict(init_vals))

times = []
temps = []

lines = f.readlines()

#Mark empty lines and comments
for i in range(0,len(lines)):
    if lines[i][0] in ['\n','#']:
        lines[i] = ''
    lines[i] = lines[i].strip() #Remove LF, CR and spaces from all lines

#Remove all empty lines, including the ones just marked as empty
for i in range(0,lines.count('')):
    lines.remove('')

current_time = 0
#Notice, the current implementation will fail if first line is not a time indication

current_temp = 0
current_time = 0
for line in lines:
    row = line.split(';')
    param = row[0].lower()
    value = float(row[1])
    
    if param == 'time': #New time step, store the old values
        vals = zip(keys,[current_time,current_temp])
        params.append(dict(vals))
        current_time += value
    if param == 'temp':
        current_temp = value
f.close()

print params
