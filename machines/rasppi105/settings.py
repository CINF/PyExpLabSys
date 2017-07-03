#pylint: disable-all

user = 'mgw'
passwd = 'mgw'
dateplot_table = 'dateplots_mgw'
setup = 'palle'

channels = {}
channels[0] = {'host':'rasppi24','port':9000,
               'command':'M11213502A', 'codename':'mgw_reactor_pressure',
               'comp_value': 1}


channels[1] = {'host':'rasppi24','port':9000,
               'command':'M11200362B', 'codename':'mgw_mfc_flow_01',
               'comp_value': 0.1}


channels[2] = {'host':'rasppi37','port':9000,
               'command':'21984839', 'codename':'mgw_mfc_flow_02',
               'comp_value': 0.1}


channels[3] = {'host':'rasppi37','port':9000,
               'command':'21984838', 'codename':'mgw_mfc_flow_03',
               'comp_value': 0.1}

channels[4] = {'host':'rasppi103','port':9000,
               'command':'actual_voltage_1', 'codename':'mgw_heater_voltage_1',
               'comp_value': 0.1}

channels[5] = {'host':'rasppi103','port':9000,
               'command':'actual_voltage_2', 'codename':'mgw_heater_voltage_2',
               'comp_value': 0.1}

channels[6] = {'host':'rasppi103','port':9000,
               'command':'actual_current_1', 'codename':'mgw_heater_current_1',
               'comp_value': 0.1}

channels[7] = {'host':'rasppi103','port':9000,
               'command':'actual_current_2', 'codename':'mgw_heater_current_2',
               'comp_value': 0.1}


