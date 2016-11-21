#pylint: disable-all

user = 'mgw'
passwd = 'mgw'
dateplot_table = 'dateplots_mgw'
setup = 'palle'

channels = {}
channels[0] = {'host':'rasppi105','port':9000,
               'command':'3F2320902001', 'codename':'mgw_mfc_flow_02',
               'comp_value': 0.1}

channels[1] = {'host':'rasppi105','port':9000,
               'command':'3F2320901001', 'codename':'mgw_mfc_flow_03',
               'comp_value': 0.1}

