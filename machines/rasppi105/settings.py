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

