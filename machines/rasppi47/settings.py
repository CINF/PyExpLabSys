#pylint: disable-all

user = 'furnaceroom307'
passwd = 'furnaceroom307'
dateplot_table = 'dateplots_furnaceroom307'
setup = 'furnaceroom307'
port_number = 9007

channels = {}
channels[0] = {'host':'localhost','port':9000,
               'command':'setpoint', 'codename':'fr307_furnace_1_S',
               'comp_value': 0.25}


channels[1] = {'host':'localhost','port':9000,
               'command':'dutycycle', 'codename':'fr307_furnace_1_dutycycle',
               'comp_value': 0.001}

channels[2] = {'host':'localhost','port':9000,
               'command':'pid_p', 'codename':'fr307_furnace_1_pid_p',
               'comp_value': 0.001}

channels[3] = {'host':'localhost','port':9000,
               'command':'pid_i', 'codename':'fr307_furnace_1_pid_i',
               'comp_value': 0.001}

