#pylint: disable-all

controller_hostname = 'rasppi47'
controller_push_port = 8500
controller_pull_port = 9000


channels = {}
channels[0] = {'host':'rasppi24','port':9000,
               'command':'M11213502A', 'codename':'mgw_reactor_pressure',
               'comp_value': 1}


channels[1] = {'host':'rasppi24','port':9000,
               'command':'M11200362B', 'codename':'mgw_mfc_flow_01',
               'comp_value': 0.1}
