def read_ms_channel_list(file='channel_list.txt'):
    channel_list = {}
    channel_list['ms'] = {}
    channel_list['meta'] = {}

    f = open(file, 'r')
    file = f.read()
    lines = file.split('\n')

    data_lines = []
    for line in lines:
        if (len(line) > 0) and (not line[0] == '#'):
            data_lines.append(line)


    i = 1
    for line in data_lines:
        items = line.split(':')
        if items[0].lower().strip() == 'comment':
            comment = items[1].strip()

        if items[0].lower().strip() == 'autorange':
            autorange = items[1].lower().strip() == 'yes'

        if items[0].lower().strip() == 'ms_channel':
            params = items[1].split(',')
            for j in range(0,len(params)):
                params[j] = params[j].strip()
            label = params[params.index('masslabel')+1].strip()
            speed = params[params.index('speed')+1].strip()
            mass = params[params.index('mass')+1].strip()
            amp_range = params[params.index('amp_range')+1].strip()
            channel_list['ms'][i] = {'masslabel':label, 'speed':speed,'mass':mass,'amp_range':amp_range}
            i += 1
        
    channel_list['ms'][0] = {'comment':comment, 'autorange':autorange}

    return channel_list

if __name__ == '__main__':
    print read_ms_channel_list()
