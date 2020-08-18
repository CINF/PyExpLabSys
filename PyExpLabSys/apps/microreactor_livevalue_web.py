"""Live vaslues used for the microreacotr setups"""
# pylint: disable=no-member
import socket
from datetime import datetime
import time as t
import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
from PyExpLabSys.common.supported_versions import python3_only
python3_only(__file__)

###### Python functions needed and global variables ##########3

FLOWNAMES = {
        'flow1':'Flow 1 [O2]',
        'flow2':'Flow 2 [He]',
        'flow3':'Flow 3 [H2]',
        'flow4':'Flow 4 [None]',
        'flow5':'Flow 5 [Ar]',
        'flow6':'Flow 6 [CO]',
        }

NAMES = [
        'thermocouple_temp', 'rtd_temp', 'chamber_pressure', 'reactor_pressure', 'buffer_pressure',
        'containment_pressure', 'flow1', 'flow2', 'flow3', 'flow4', 'flow5', 'flow6',
        ]
INTERVAL = 5
HOURS = 18
MAX_LENGTH = int(HOURS*3600/INTERVAL)

ALL_DATA = {name: {'x': [], 'y': []} for name in NAMES}

def communicate_sock(network_adress, com, port=9000):
    """This is the socekt communications function"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1)

    try:
        command = com.encode()
        sock.sendto(command, (network_adress, port))
        received_bytes = sock.recv(1024)#
        received = received_bytes.decode('ascii')
        #expected string recived: 'time_since_epoch,value'
        value = float(received[received.find(',')+1:])
    except ValueError:
        value = -500.0#None

    return value

def all_values_update():
    """Function to call update all values"""
    time = datetime.now()
    
    #Temperature values from thermocouple and RTD
    thermocouple_temp = communicate_sock('rasppi12', 'microreactorng_temp_sample#raw')
    rtd_temp = communicate_sock('rasppi05', 'temperature#raw')
    if isinstance(rtd_temp, float):
        rtd_temp = round(rtd_temp, 1)
    
    #Pressure values from NextGeneration setup
    chamber_pressure = communicate_sock('microreactorng', 'read_pressure#labview', port=7654)
    reactor_pressure = communicate_sock('rasppi16', 'M11200362H#raw')
    if reactor_pressure == 0:
        reactor_pressure = 1e-4
    if isinstance(reactor_pressure, float):
        reactor_pressure = round(reactor_pressure, 3)
    buffer_pressure = communicate_sock('rasppi36', 'microreactorng_pressure_buffer#raw')
    containment_pressure = communicate_sock('microreactorng', 'read_containment#labview', port=7654)

    #Flow values from NextGeneration setup
    flow1 = communicate_sock('rasppi16', 'M11200362C#raw')
    flow2 = communicate_sock('rasppi16', 'M11200362A#raw')
    flow3 = communicate_sock('rasppi16', 'M11200362E#raw')
    flow4 = communicate_sock('rasppi16', 'M11200362D#raw')
    flow5 = communicate_sock('rasppi16', 'M11210022B#raw')
    flow6 = communicate_sock('rasppi16', 'M11200362G#raw')

    for i in [flow1, flow2, flow3, flow4, flow5, flow6]:
        if i is not None and len(str(i)) > 3:
            i = round(i, 2)

    values = [
        thermocouple_temp, rtd_temp, chamber_pressure, reactor_pressure, buffer_pressure,
        containment_pressure, flow1, flow2, flow3, flow4, flow5, flow6,
        ]

    for i, elem in enumerate(NAMES):
        ALL_DATA[NAMES[i]]['x'].append(time)
        ALL_DATA[NAMES[i]]['y'].append(values[i])
        if len(ALL_DATA[NAMES[i]]['x']) > MAX_LENGTH:
            ALL_DATA[NAMES[i]]['x'].pop(0)
            ALL_DATA[NAMES[i]]['y'].pop(0)
    print(ALL_DATA['thermocouple_temp']['x'][-1])
    t.sleep(1)

### Colours for dash app and plots ####
COLOURS = {
    'background':'#607D8B',
    'text1': '#BDBDBD',
    'text': '#5e7366',
    'main_chamber_pressure':'#AFB42B',
    'thermocouple_temp':'#FF9800',
    'rtd_temp':'#795548',
    'containment_pressure':'#F44336',
    'buffer_pressure':'#0097A7',
    'reactor_pressure':'#3F51B5',
    'flow1': '#FBC02D',
    'flow2': '#9C27B0',
    'flow3':'#1976D2',
    'flow4':'#a52a2a',
    'flow5':'#388E3C',
    'flow6':'#616161',
    'paper_bgcolor':'#020202',
    'plot_bgcolor':'#191A1A',
    }



APP = dash.Dash(__name__)
APP.css.append_css({'external_url': 'https://cdn.rawgit.com/plotly/dash-app-stylesheets/2d266c578d2a6e8850ebce48fdb52759b2aef506/stylesheet-oil-and-gas.css'})


                     ############# Layout of application ####################
r"""
.  ------------------------------------------------------------------------------------  .
|                                         TITLE                                          |
| . _________________________________________________________ .  . __________________ .  |
| |   __  __       _          _____                 _         |  |       _______      |  |
| |  |  \/  |     (_)        / ____|               | |        |  |      |__   __|     |  |
| |  | \  / | __ _ _ _ __   | |  __ _ __ __ _ _ __ | |__      |  |         | |        |  |
| |  | |\/| |/ _` | | '_ \  | | |_ | '__/ _` | '_ \| '_ \     |  |         | |        |  |
| |  | |  | | (_| | | | | | | |__| | | | (_| | |_) | | | |    |  |         | |        |  |
| |  |_|  |_|\__,_|_|_| |_|  \_____|_|  \__,_| .__/|_| |_|    |  |         |/\        |  |
| |                                          | |              |  |         /  \       |  |
| |                                          |_|              |  |        / /\ \      |  |
| , _________________________________________________________ ,  |       / ____ \     |  |
|                                                                |      /_/__  \_\    |  |
| . _______________ . . ________________ . . ________________ .  |      |  _ \        |  |
| |                 | |                  | |                  |  |      | |_) |       |  |
| |              ___| | _      ____ _______ _____             |  |      |  _ <        |  |
| |             |  __ \| |    / __ \__   __/ ____|            |  |      | |_) |       |  |
| |             | |__) | |   | |  | | | | | (___              |  |      |____/        |  |
| |             |  ___/| |   | |  | | | |  \___ \             |  |      | |           |  |
| |             | | | || |___| |__| | | |  ____) |            |  |      | |           |  |
| |             |_| | ||______\____/  |_| |_____/             |  |      | |           |  |
| |       __        | |       __         | |       ___        |  |      | |____       |  |
| |      /_ |       | |      |__ \       | |      |___ \      |  |      |______|      |  |
| |       | |       | |         ) |      | |        __) |     |  |      |  ____|      |  |
| |       | |       | |        / /       | |       |__ <      |  |      | |__         |  |
| |       | |       | |       / /_       | |       ___) |     |  |      |  __|        |  |
| |       |_|       | |      |____|      | |      |____/      |  |      | |____       |  |
| |                 | |                  | |                  |  |      |______|      |  |
| , _______________ , , ________________ , , ________________ ,  , __________________ ,  |
.  ------------------------------------------------------------------------------------  .
"""

APP.layout = html.Div(style={'backgroundColor': COLOURS['paper_bgcolor']}, children=[
        dcc.Interval(
            id='interval-component', #id for update INTERVAL
            interval=INTERVAL*1000, #time in ms between execution
            n_intervals=0#number of times
            ),

        #### headline ###
    html.Div(
                [
                    html.H1(
                        'Dashboard of MicroreactorANH',
                        style={'textAlign': 'center', 'color': COLOURS['text']},
                        className='twelve columns'
                        )
                ], className='row'),
    ### Main Plot ####
    html.Div([
        html.Div([
            html.Div([dcc.Graph(id='plot_press',
                                animate=True,
                                className='twelve')],
                     className='row'),
            ### Three Plots ###
            html.Div([
                dcc.Graph(id='plot_temp',
                          animate=True,
                          className='four columns'),
                dcc.Graph(id='plot_flow',
                          animate=True,
                          className='four columns'),
                dcc.Graph(id='plot_not_used',
                          animate=True,
                          className='four columns')],
                     className='row')],
                 className='eight columns'),
        ### Table ###
        html.Div([
            html.Table(id='table_pressure')],
                 className='four columns'),],
             className='row'),

    html.Div(id='intermediate-values', style={'display':'none'})
])

############## CALL BACK FUNCTIONS ###############

@APP.callback(
        Output(component_id='intermediate-values', component_property='children'),
        [Input('interval-component', 'n_intervals')])
def update_values(n):
    """Function to call update all values"""
    all_values_update()


@APP.callback(
        Output(component_id='plot_press', component_property='figure'),
        [Input(component_id='intermediate-values', component_property='children')]
        )
def update_press_graph(n):
    """Function to update pressure graph"""
    lst = ALL_DATA['containment_pressure']['y']+\
          ALL_DATA['reactor_pressure']['y']+\
          ALL_DATA['buffer_pressure']['y']+\
          ALL_DATA['chamber_pressure']['y']

    if not [i for i in lst if i is not None]:
        ymin = 0
        ymax = 1
    else:
        ymin = min(i for i in lst if i is not None) * 0.999
        ymax = max(i for i in lst if i is not None) * 1.001
    data = [
        go.Scatter(
            ALL_DATA['containment_pressure'],
            marker=dict(color=COLOURS['containment_pressure'])
            ),
        go.Scatter(
            ALL_DATA['reactor_pressure'],
            marker=dict(color=COLOURS['reactor_pressure'])
            ),
        go.Scatter(
            ALL_DATA['buffer_pressure'],
            marker=dict(color=COLOURS['buffer_pressure'])
            )]
    layout = go.Layout(
        xaxis=dict(range=[ALL_DATA['thermocouple_temp']['x'][0],
                          ALL_DATA['thermocouple_temp']['x'][-1]]),
        yaxis=dict(exponentformat='e', type='log'),
        height=400,
        margin={'l':35, 'r':35, 'b':35, 't':45},
        hovermode='closest',
        legend={'orientation':'h'},
        title='Pressures',
        plot_bgcolor='#191A1A',
        paper_bgcolor='#020202',
        showlegend=False,
        font=dict(color=COLOURS['text1'])
        )
    return {'data':data, 'layout':layout}

@APP.callback(
        Output(component_id='plot_temp', component_property='figure'),
        [Input(component_id='intermediate-values', component_property='children')]
        )
def update_temp_graph(n):
    """Function to updtae temperature plots"""
    if len([i for i in (ALL_DATA['thermocouple_temp']['y']+ALL_DATA['rtd_temp']['y']) if i is not None]) == 0:
        ymin = 0
        ymax = 1
    else:
        y_axis = [i for i in (ALL_DATA['rtd_temp']['y']+ALL_DATA['thermocouple_temp']['y']) if i is not None]
        ymin = min(y_axis) * 0.999
        ymax = max(y_axis) * 1.001
    data = [
        go.Scatter(
            ALL_DATA['rtd_temp'],
            marker=dict(color=COLOURS['rtd_temp'])
            ),
        go.Scatter(
            ALL_DATA['thermocouple_temp'],
            marker=dict(color=COLOURS['thermocouple_temp'])
            )]
    layout = go.Layout(
        xaxis=dict(range=[ALL_DATA['thermocouple_temp']['x'][0],
                          ALL_DATA['thermocouple_temp']['x'][-1]]),
        yaxis=dict(range=[ymin, ymax]),
        height=300,
        margin={'l':35, 'r':35, 'b':35, 't':45},
        hovermode='closest',
        legend={'orientation':'h'},
        title='Temperature',
        plot_bgcolor='#191A1A',
        paper_bgcolor='#020202',
        showlegend=False,
        font=dict(color=COLOURS['text1'])
        )
    return {'data':data, 'layout':layout}


@APP.callback(
        Output(component_id='plot_flow', component_property='figure'),
        [Input(component_id='intermediate-values', component_property='children')]
        )
def update_flow_graph(n):
    """Function to update flows plot"""

    lst = ALL_DATA['flow1']['y']+ALL_DATA['flow2']['y']+ALL_DATA['flow3']['y']+ALL_DATA['flow4']['y']+ALL_DATA['flow5']['y']+ALL_DATA['flow6']['y']

    if len([i for i in lst if i is not None]) == 0:
        ymin = 0
        ymax = 6
    else:
        ymin = 0
        ymax = max(i for i in lst if i is not None) * 1.001
        if ymax < 5.5:
            ymax = 6
        else:
            ymax = 10
    data = [
        go.Scatter(
            ALL_DATA['flow1'],
            marker=dict(color=COLOURS['flow1'])
            ),
        go.Scatter(
            ALL_DATA['flow2'],
            marker=dict(color=COLOURS['flow2'])
            ),
        go.Scatter(
            ALL_DATA['flow3'],
            marker=dict(color=COLOURS['flow3'])
            ),
        go.Scatter(
            ALL_DATA['flow4'],
            marker=dict(color=COLOURS['flow4'])
            ),
        go.Scatter(
            ALL_DATA['flow5'],
            marker=dict(color=COLOURS['flow5'])
            ),
        go.Scatter(
            ALL_DATA['flow6'],
            marker=dict(color=COLOURS['flow6']),)]
    layout = go.Layout(
        xaxis=dict(range=[ALL_DATA['thermocouple_temp']['x'][0],
                          ALL_DATA['thermocouple_temp']['x'][-1]]),
        yaxis=dict(range=[0, ymax]),
        height=300,
        margin={'l':35, 'r':35, 'b':35, 't':45},
        hovermode='closest',
        legend={'orientation':'h'},
        title='Flows',
        plot_bgcolor='#191A1A',
        paper_bgcolor='#020202',
        showlegend=False,
        font=dict(color=COLOURS['text1'])
        )

    return {'data':data, 'layout':layout}

@APP.callback(
        Output(component_id='plot_not_used', component_property='figure'),
        [Input(component_id='intermediate-values', component_property='children')]
        )
def update_not_in_use_graph(n):
    """Function to update Mainchamber plot"""

    lst = ALL_DATA['chamber_pressure']['y']

    if len([i for i in lst if i is not None]) == 0:
        ymin = 0
        ymax = 1
    else:
        ymin = min(i for i in lst if i is not None)*0.999
        ymax = max(i for i in lst if i is not None)*1.001
    data = [
        go.Scatter(
            ALL_DATA['chamber_pressure'],
            marker=dict(color=COLOURS['main_chamber_pressure'])
            )]
    layout = go.Layout(
        xaxis=dict(range=[ALL_DATA['thermocouple_temp']['x'][0],
                          ALL_DATA['thermocouple_temp']['x'][-1]]),
        yaxis=dict(exponentformat='e', type='log'),
        height=300,
        margin={'l':35, 'r':35, 'b':35, 't':45},
        hovermode='closest',
        legend={'orientation':'h'},
        title='Main Chamber Pressure',
        plot_bgcolor='#191A1A',
        paper_bgcolor='#020202',
        showlegend=False,
        font=dict(color=COLOURS['text1'])
        )
    return {'data':data, 'layout':layout}

@APP.callback(
    Output(component_id='table_pressure', component_property='children'),
    [Input('intermediate-values', 'children')])
def update_table(n):
    """"Update table values"""
    ### Pressure values ###
    chamber_pressure = ALL_DATA['chamber_pressure']
    reactor_pressure = ALL_DATA['reactor_pressure']
    buffer_pressure = ALL_DATA['buffer_pressure']
    containment_pressure = ALL_DATA['containment_pressure']
    thermocouple_temp = ALL_DATA['thermocouple_temp']
    rtd_temp = ALL_DATA['rtd_temp']

    ## Flows Values ###
    flow1 = ALL_DATA['flow1']
    flow2 = ALL_DATA['flow2']
    flow3 = ALL_DATA['flow3']
    flow4 = ALL_DATA['flow4']
    flow5 = ALL_DATA['flow5']
    flow6 = ALL_DATA['flow6']

    if flow5['y'] is None:
        flow5['y'] = -1
    bgstyle = {'textAlign':'center',
               'color': COLOURS['text'],
               'backgroundColor':COLOURS['plot_bgcolor']
               }
    bgstyle_header = {'color':COLOURS['text1']}
    #Table
    out = (
        [
            html.Tr(
                [html.Th('#'), html.Th('Name'), html.Th('Time'), html.Th('Value')],
                style=bgstyle_header)
            ]+
        [html.Tr([
            html.Td(style={'backgroundColor':COLOURS['main_chamber_pressure']}),
            html.Td('Main Chamber Pressure'),
            html.Td(chamber_pressure['x'][-1].strftime("%H:%M:%S")),
            html.Td(format(chamber_pressure['y'][-1], '0.2e'))],
                 style=bgstyle)]+
        [html.Tr([
            html.Td(style={'backgroundColor':COLOURS['reactor_pressure']}),
            html.Td('Reactor Pressure'),
            html.Td(reactor_pressure['x'][-1].strftime("%H:%M:%S")),
            html.Td(format(reactor_pressure['y'][-1], '0.2e'))],
                 style=bgstyle)]+
        [html.Tr([
            html.Td(style={'backgroundColor':COLOURS['buffer_pressure']}),
            html.Td('Buffer Pressure'),
            html.Td(buffer_pressure['x'][-1].strftime("%H:%M:%S")),
            html.Td(format(buffer_pressure['y'][-1], '0.2e'))],
                 style=bgstyle)]+
        [html.Tr([
            html.Td(style={'backgroundColor':COLOURS['containment_pressure']}),
            html.Td('Containment Pressure'),
            html.Td(containment_pressure['x'][-1].strftime("%H:%M:%S")),
            html.Td(format(containment_pressure['y'][-1], '0.2e'))],
                 style=bgstyle)]+
        [html.Tr([
            html.Td(style={'backgroundColor':COLOURS['thermocouple_temp']}),
            html.Td('Temperature TC'),
            html.Td(thermocouple_temp['x'][-1].strftime("%H:%M:%S")),
            html.Td(format(thermocouple_temp['y'][-1], '0.3'))],
                 style=bgstyle)]+
        [html.Tr([
            html.Td(style={'backgroundColor':COLOURS['rtd_temp']}),
            html.Td('Temperature RTD'),
            html.Td(rtd_temp['x'][-1].strftime("%H:%M:%S")),
            html.Td(format(rtd_temp['y'][-1], '0.3'))],
                 style=bgstyle)]+
        [html.Tr([
            html.Td(style={'backgroundColor':COLOURS['flow1']}),
            html.Td(FLOWNAMES['flow1']),
            html.Td(flow1['x'][-1].strftime("%H:%M:%S")),
            html.Td(format(flow1['y'][-1], '0.2'))],
                 style=bgstyle)]+
        [html.Tr([
            html.Td(style={'backgroundColor':COLOURS['flow2']}),
            html.Td(FLOWNAMES['flow2']),
            html.Td(flow2['x'][-1].strftime("%H:%M:%S")),
            html.Td(format(flow2['y'][-1], '0.2'))],
                 style=bgstyle)]+
        [html.Tr([
            html.Td(style={'backgroundColor':COLOURS['flow3']}),
            html.Td(FLOWNAMES['flow3']),
            html.Td(flow3['x'][-1].strftime("%H:%M:%S")),
            html.Td(format(flow3['y'][-1], '0.2'))],
                 style=bgstyle)]+
        [html.Tr([
            html.Td(style={'backgroundColor':COLOURS['flow4']}),
            html.Td(FLOWNAMES['flow4']),
            html.Td(flow4['x'][-1].strftime("%H:%M:%S")),
            html.Td(format(flow4['y'][-1], '0.2'))],
                 style=bgstyle)]+
        [html.Tr([
            html.Td(style={'backgroundColor':COLOURS['flow5']}),
            html.Td(FLOWNAMES['flow5']),
            html.Td(flow5['x'][-1].strftime("%H:%M:%S")),
            html.Td(format(flow5['y'][-1], '0.2'))],
                 style=bgstyle)]+
        [html.Tr([
            html.Td(style={'backgroundColor':COLOURS['flow6']}),
            html.Td(FLOWNAMES['flow6']),
            html.Td(flow6['x'][-1].strftime("%H:%M:%S")),
            html.Td(format(flow6['y'][-1], '0.2'))],
                 style=bgstyle)])
    return out


if __name__ == '__main__':
    APP.run_server(host='0.0.0.0', debug=True, port=8050)
