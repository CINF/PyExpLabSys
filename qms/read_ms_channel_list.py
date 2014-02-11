#TODO: This function should either be integrated into qms.py or be turned into a real module
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


    ms = 1
    meta = 1
    for line in data_lines:
        items = line.split(':')
        key = items[0].lower().strip()
        if  key == 'comment':
            comment = items[1].strip()

        if key == 'autorange':
            autorange = items[1].lower().strip() == 'yes'

        if key == 'ms_channel':
            params = items[1].split(',')
            for j in range(0,len(params)):
                params[j] = params[j].strip()
            label = params[params.index('masslabel')+1]
            speed = params[params.index('speed')+1]
            mass = params[params.index('mass')+1]
            amp_range = params[params.index('amp_range')+1]
            channel_list['ms'][ms] = {'masslabel':label, 'speed':speed,'mass':mass,'amp_range':amp_range}
            ms += 1

        if key == 'meta_channel':
            params = items[1].split(',')
            for j in range(0,len(params)):
                params[j] = params[j].strip()
            host = params[params.index('host')+1]
            port = params[params.index('port')+1]
            label = params[params.index('label')+1]
            command = params[params.index('command')+1]
            channel_list['meta'][meta] = {'host':host, 'port':port,'label':label,'command':command}
            meta += 1

    #TODO: The channel list format should be changed so that the general
    #      parameters are in a third dictionary key
    channel_list['ms'][0] = {'comment':comment, 'autorange':autorange}

    return channel_list

if __name__ == '__main__':
    print read_ms_channel_list()
