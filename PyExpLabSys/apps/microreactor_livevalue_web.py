import dash
from dash.dependencies import Input, Output, Event, State
import dash_core_components as dcc
import dash_html_components as html
import random
import plotly
import socket
from datetime import datetime
import plotly.graph_objs as go
from collections import deque
import time as t


###### Python functions needed and global variables ##########3

flownames = {
        'flow1':'Flow 1 [O2]',
        'flow2':'Flow 2 [He]',
        'flow3':'Flow 3 [H2]',
        'flow4':'Flow 4 [None]',
        'flow5':'Flow 5 [Ar]',
        'flow6':'Flow 6 [CO]',
        }

names = ['TCtemp','RTDtemp','chamber_pressure','reactor_pressure','buffer_pressure','containment_pressure','flow1','flow2','flow3','flow4','flow5','flow6']
interval = 5
hours = 18
maxlen = int(hours*3600/interval) 
#X = deque(maxlen=maxlen)
#Y = deque(maxlen=maxlen)
all_data = {}
for name in names:
    all_data[name] = {'x':[],'y':[]}

def communicate_sock(network_adress,com,port=9000):
    ''' This is the funtion '''
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1)
    
    try:
        command = com.encode()
       # print(command)
#        with socket_lock:    
        sock.sendto(command,(network_adress,port))
        received = sock.recv(1024)
        received = received.decode('ascii')
        value = float(received[received.find(',')+1:])
    except:
        value = None
    
    return value  

#while True:
def all_values_update():
    ''' Function to call update all values '''
    time = datetime.now()#.strftime("%H:%M:%S")
    TCtemp = communicate_sock('rasppi12','microreactorng_temp_sample#raw')
    RTDtemp = communicate_sock('rasppi05','temperature#raw')
    if RTDtemp is not None and len(str(RTDtemp)) > 5:
        RTDtemp = round(RTDtemp,1)
    chamber_pressure = communicate_sock('microreactorng','read_pressure#labview',port=7654)
    reactor_pressure = communicate_sock('rasppi16','M11200362H#raw')
    if reactor_pressure == 0:
        reactor_pressure = 1e-4
    if reactor_pressure is not None and len(str(reactor_pressure)) > 5:
        reactor_pressure = round(reactor_pressure,3)
    buffer_pressure = communicate_sock('rasppi36','microreactorng_pressure_buffer#raw')
    containment_pressure = communicate_sock('microreactorng','read_containment#labview',port=7654)
    flow1 = communicate_sock('rasppi16','M11200362C#raw')
    flow2 = communicate_sock('rasppi16','M11200362A#raw')
    flow3 = communicate_sock('rasppi16','M11200362E#raw')
    flow4 = communicate_sock('rasppi16','M11200362D#raw')
    flow5 = communicate_sock('rasppi16','M11210022B#raw')
    flow6 = communicate_sock('rasppi16','M11200362G#raw')
    
    for i in [flow1,flow2,flow3,flow4,flow5,flow6]:
        if i is not None and len(str(i)) > 3:
            i = round(i,2)

    names = ['TCtemp','RTDtemp','chamber_pressure','reactor_pressure','buffer_pressure','containment_pressure','flow1','flow2','flow3','flow4','flow5','flow6']
    values = [TCtemp,RTDtemp,chamber_pressure,reactor_pressure,buffer_pressure,containment_pressure,flow1,flow2,flow3,flow4,flow5,flow6]
    for i in range(len(names)):
        all_data[names[i]]['x'].append(time)
        all_data[names[i]]['y'].append(values[i])
        if len(all_data[names[i]]['x']) > maxlen:
            all_data[names[i]]['x'].pop(0)
            all_data[names[i]]['y'].pop(0)
    print(all_data['TCtemp']['x'][-1])#,RTDtemp,chamber_pressure,reactor_pressure,buffer_pressure,containment_pressure,flow1,flow2,flow3,flow4,flow5,flow6
    t.sleep(1)

### Colours for dash app and plots ####
colors = {
    'background':'#607D8B',# '#191A1A',
    'text1': '#BDBDBD',# '#af5f5f',
    'text': '#5e7366',#'#BDBDBD',#
    'main_chamber_pressure':'#AFB42B',#009000',
    'TCtemp':'#FF9800',#87afd7',
    'RTDtemp':'#795548',#735e6b',
    'containment_pressure':'#F44336',#c080d0',
    'buffer_pressure':'#0097A7',#404040',
    'reactor_pressure':'#3F51B5',#84a3e3',
    'flow1': '#FBC02D',#af5f5f',
    'flow2': '#9C27B0',#512DA8',#5e7366',
    'flow3':'#1976D2',#009000',
    'flow4':'#a52a2a',#87afd7',
    'flow5':'#388E3C',#735e6b',
    'flow6':'#616161',#c080d0',
    'paper_bgcolor':'#020202',
    'plot_bgcolor':'#191A1A',
    }



app = dash.Dash(__name__)
app.css.append_css({'external_url': 'https://cdn.rawgit.com/plotly/dash-app-stylesheets/2d266c578d2a6e8850ebce48fdb52759b2aef506/stylesheet-oil-and-gas.css'})  # noqa: E501
#app.css.append_css({'external_url':'https://codepen.io/chriddyp/pen/bWLwgP.css'})
#app.css.append_css({'external_url':'https://maxcdn.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap.min.css'})
#app.scripts.append_script({'external_url': 'https://ajax.googleapis.com/ajax/libs/jquery/3.3.1/jquery.min.js'})
#app.scripts.append_script({'external_url': 'https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.3/umd/popper.min.js'})
#app.scripts.append_script({'external_url': 'https://maxcdn.bootstrapcdn.com/bootstrap/4.1.3/js/bootstrap.min.js'})
############# LAYOUT USING ####################
app.layout = html.Div(style={'backgroundColor': colors['paper_bgcolor']},children= [
        dcc.Interval(
            id='interval-component',#id for update interval
            interval=interval*1000, #time in ms between execution
            n_intervals=0#number of times
            ),

        #### headline ###
            html.Div(
                [ 
                   html.H1(
                       'Dashboard of MicroreactorANH',
                       style={'textAlign': 'center', 'color': colors['text']},
                       className='twelve columns'
                       )
                ],className='row'),
           # html.Br(),
### Here I should implement somthing nice like 3 rows or something like that maybe with live values I dont know###
html.Div([
    html.Div([
        html.Div([dcc.Graph(id='plot_press',
                            animate = True, 
                            className='twelve')
        ],className='row'),
        html.Div([
                  dcc.Graph(id='plot_temp',
                            animate = True, 
                            className='four columns'),
                  dcc.Graph(id='plot_flow',
                              animate=True,
                              className='four columns'),
                  dcc.Graph(id='plot_not_used',
                              animate=True,
                              className='four columns')
        ],className='row')
    ],className='eight columns'),
    html.Div([
            html.Table(id='table_pressure')
             ],className='four columns'),
],className='row'),            



###############################
html.Div(id='intermediate-values',style={'display':'none'})
])

############## CALL BACK FUNCTIONS ###############

@app.callback(
        Output(component_id='intermediate-values', component_property='children'),
        [Input('interval-component', 'n_intervals')])

def update_values(n):
    ''' Function to call update all values '''
#    time = datetime.now()#.strftime("%H:%M:%S")
#    TCtemp = communicate_sock('rasppi12','microreactorng_temp_sample#raw')
#    RTDtemp = communicate_sock('rasppi05','temperature#raw')
#    if RTDtemp is not None and len(str(RTDtemp)) > 5:
#        RTDtemp = round(RTDtemp,1)
#    chamber_pressure = communicate_sock('microreactorng','read_pressure#labview',port=7654)
#    reactor_pressure = communicate_sock('rasppi16','M11200362H#raw')
#    if reactor_pressure == 0:
#        reactor_pressure = 1e-4
#    buffer_pressure = communicate_sock('rasppi36','microreactorng_pressure_buffer#raw')
#    containment_pressure = communicate_sock('microreactorng','read_containment#labview',port=7654)
#    flow1 = communicate_sock('rasppi16','M11200362C#raw')
#    flow2 = communicate_sock('rasppi16','M11200362A#raw')
#    flow3 = communicate_sock('rasppi16','M11200362E#raw')
#    flow4 = communicate_sock('rasppi16','M11200362D#raw')
#    flow5 = communicate_sock('rasppi16','M11210022B#raw')
#    flow6 = communicate_sock('rasppi16','M11200362G#raw')
#    names = ['TCtemp','RTDtemp','chamber_pressure','reactor_pressure','buffer_pressure','containment_pressure','flow1','flow2','flow3','flow4','flow5','flow6']
#    values = [TCtemp,RTDtemp,chamber_pressure,reactor_pressure,buffer_pressure,containment_pressure,flow1,flow2,flow3,flow4,flow5,flow6]
#    for i in range(len(names)):
#        all_data[names[i]]['x'].append(time)
#        all_data[names[i]]['y'].append(values[i])
#        if len(all_data[names[i]]['x']) > maxlen:
#            all_data[names[i]]['x'].pop(0)
#            all_data[names[i]]['y'].pop(0)
    all_values_update()

    return n# time,TCtemp,RTDtemp,chamber_pressure,reactor_pressure,buffer_pressure,containment_pressure,flow1,flow2,flow3,flow4,flow5,flow6


@app.callback(
        Output(component_id='plot_press',component_property='figure'),
        [Input(component_id='intermediate-values',component_property='children')]
        )
def update_press_graph(input1):
    ''' FUNCTIONS TO UPDATE PRESS PLOT  '''
    
    lst = all_data['containment_pressure']['y']+all_data['reactor_pressure']['y']+all_data['buffer_pressure']['y']+all_data['chamber_pressure']['y']

    if len([i for i in lst if i is not None]) == 0:
        ymin = 0
        ymax = 1
    else:
        ymin = min(i for i in lst if i is not None)*0.999
        ymax = max(i for i in lst if i is not None)*1.001
    data = [
            go.Scatter(
                all_data['containment_pressure'],
                marker = dict(color=colors['containment_pressure'])
            ),
            go.Scatter(
                all_data['reactor_pressure'],
                marker = dict(color=colors['reactor_pressure'])
            ),
            go.Scatter(
                all_data['buffer_pressure'],
                marker = dict(color=colors['buffer_pressure'])
            ),
           # go.Scatter(
           #     all_data['chamber_pressure']
           # )
            ] 
    layout = go.Layout( 
            xaxis=dict(range=[all_data['TCtemp']['x'][0], all_data['TCtemp']['x'][-1]]),
            yaxis=dict(exponentformat='e',type='log'),
            height = 400,
            margin = {'l':35,'r':35,'b':35,'t':45},
            hovermode='closest',
            legend={'orientation':'h'},
            title='Pressures',
            plot_bgcolor='#191A1A',
            paper_bgcolor='#020202',
            showlegend = False,
            font=dict(color=colors['text1'])
            )
    return {'data':data, 'layout':layout}

@app.callback(
        Output(component_id='plot_temp',component_property='figure'),
        [Input(component_id='intermediate-values',component_property='children')]
        )
def update_temp_graph(input1):
    ''' FUNCTIONS TO UPDATE TEMPERATURE PLOT  '''
    if len([i for i in (all_data['TCtemp']['y']+all_data['RTDtemp']['y']) if i is not None]) == 0:
        ymin = 0
        ymax = 1
    else:
        ymin = min(i for i in (all_data['RTDtemp']['y']+all_data['TCtemp']['y']) if i is not None)*0.999
        ymax = max(i for i in (all_data['RTDtemp']['y']+all_data['TCtemp']['y']) if i is not None)*1.001
    data = [
            go.Scatter(
                all_data['RTDtemp'],
                marker = dict(color=colors['RTDtemp'])
            ),
            go.Scatter(
                all_data['TCtemp'],
                marker = dict(color=colors['TCtemp'])
            )] 
    layout = go.Layout( 
            xaxis=dict(range=[all_data['TCtemp']['x'][0], all_data['TCtemp']['x'][-1]]),
            yaxis=dict(range=[ymin,ymax]),
            height = 300,
            margin = {'l':35,'r':35,'b':35,'t':45},
            hovermode='closest',
            legend={'orientation':'h'},
            title='Temperature',
            plot_bgcolor='#191A1A',
            paper_bgcolor='#020202',
            showlegend = False,
            font=dict(color=colors['text1'])
            )
    return {'data':data, 'layout':layout}


@app.callback(
        Output(component_id='plot_flow',component_property='figure'),
        [Input(component_id='intermediate-values',component_property='children')]
        )
def update_flow_graph(input1):
    ''' FUNCTIONS TO UPDATE FLOWS PLOT  '''
    
    lst = all_data['flow1']['y']+all_data['flow2']['y']+all_data['flow3']['y']+all_data['flow4']['y']+all_data['flow5']['y']+all_data['flow6']['y']
    
    if len([i for i in lst if i is not None]) == 0:
        ymin = 0
        ymax = 6 
    else:
        ymin = 0 #min(i for i in lst if i is not None)*0.999
        ymax = max(i for i in lst if i is not None)*1.001
        if ymax < 5:
            ymax = 6
        else:
            ymax = 10
    data = [
            go.Scatter(
                all_data['flow1'],
                marker = dict(color=colors['flow1'])
            ),
            go.Scatter(
                all_data['flow2'],
                marker = dict(color=colors['flow2'])
            ),
            go.Scatter(
                all_data['flow3'],
                marker = dict(color=colors['flow3'])
            ),
            go.Scatter(
                all_data['flow4'],
                marker = dict(color=colors['flow4'])
            ),
            go.Scatter(
                all_data['flow5'],
                marker = dict(color=colors['flow5'])
            ),
            go.Scatter(
                all_data['flow6'],
                marker = dict(color=colors['flow6']),
           )] 
    layout = go.Layout( 
            xaxis=dict(range=[all_data['TCtemp']['x'][0], all_data['TCtemp']['x'][-1]]),
            yaxis=dict(range=[0,ymax]),
            height = 300,
            margin = {'l':35,'r':35,'b':35,'t':45},
            hovermode='closest',
            legend={'orientation':'h'},
            title='Flows',
            plot_bgcolor='#191A1A',
            paper_bgcolor='#020202',
            showlegend = False,
            font=dict(color=colors['text1'])
            )
    return {'data':data, 'layout':layout}

@app.callback(
        Output(component_id='plot_not_used',component_property='figure'),
        [Input(component_id='intermediate-values',component_property='children')]
        )
def update_not_in_use_graph(input1):
    ''' FUNCTIONS TO UPDATE MAINCHAMBER PLOT  '''
    
    lst = all_data['chamber_pressure']['y']

    if len([i for i in lst if i is not None]) == 0:
        ymin = 0
        ymax = 1
    else:
        ymin = min(i for i in lst if i is not None)*0.999
        ymax = max(i for i in lst if i is not None)*1.001
    data = [
            go.Scatter(
                all_data['chamber_pressure'],
                marker = dict(color=colors['main_chamber_pressure'])
            )
            ] 
    layout = go.Layout( 
            xaxis=dict(range=[all_data['TCtemp']['x'][0], all_data['TCtemp']['x'][-1]]),
            yaxis=dict(exponentformat='e',type='log'),
            height = 300,
            margin = {'l':35,'r':35,'b':35,'t':45},
            hovermode='closest',
            legend={'orientation':'h'},
            title='Main Chamber Pressure',
            plot_bgcolor='#191A1A',
            paper_bgcolor='#020202',
            showlegend = False,
            font=dict(color=colors['text1'])
            )
    return {'data':data, 'layout':layout}

@app.callback(
       Output(component_id='table_pressure', component_property='children'),
        [Input('intermediate-values', 'children')])
def update_table(n):
  ##Pressure## 
    chamber_pressure = all_data['chamber_pressure']
    reactor_pressure = all_data['reactor_pressure']
    buffer_pressure = all_data['buffer_pressure'] 
    containment_pressure = all_data['containment_pressure']
    TCtemp = all_data['TCtemp']#values[1]# communicate_sock_temp('rasppi12','microreactorng_temp_sample#raw')
    RTDtemp = all_data['RTDtemp']#values[2]#communicate_sock_temp('rasppi05','temperature#raw')
#    if RTDtemp['y'] == None:
#        RTDtemp['y'] = 'NaN'
    
  ## Flows ###
    flow1 = all_data['flow1']
    flow2 = all_data['flow2']
    flow3 = all_data['flow3']
    flow4 = all_data['flow4']
    flow5 = all_data['flow5']
    flow6 = all_data['flow6']
    
    if flow5['y'] == None:
        flow5['y'] = -1
    bgstyle = {'textAlign':'center', 'color': colors['text'], 'backgroundColor':colors['plot_bgcolor']}
    bgstyle_header = {'color':colors['text1']}
    #Table 
    out = ([html.Tr([html.Th('#'),html.Th('Name'),html.Th('Time'),html.Th('Value')],style=bgstyle_header)]+
            [html.Tr([html.Td(style={'backgroundColor':colors['main_chamber_pressure']}),html.Td('Main Chamber Pressure'),html.Td(chamber_pressure['x'][-1].strftime("%H:%M:%S")),html.Td(format(chamber_pressure['y'][-1],'0.2e'))],style=bgstyle)]+
            [html.Tr([html.Td(style={'backgroundColor':colors['reactor_pressure']}),html.Td('Reactor Pressure'),html.Td(reactor_pressure['x'][-1].strftime("%H:%M:%S")),html.Td(format(reactor_pressure['y'][-1],'0.2e'))],style=bgstyle)]+
            [html.Tr([html.Td(style={'backgroundColor':colors['buffer_pressure']}),html.Td('Buffer Pressure'),html.Td(buffer_pressure['x'][-1].strftime("%H:%M:%S")),html.Td(format(buffer_pressure['y'][-1],'0.2e'))],style=bgstyle)]+
            [html.Tr([html.Td(style={'backgroundColor':colors['containment_pressure']}),html.Td('Containment Pressure'),html.Td(containment_pressure['x'][-1].strftime("%H:%M:%S")),html.Td(format(containment_pressure['y'][-1],'0.2e'))],style=bgstyle)]+
            [html.Tr([html.Td(style={'backgroundColor':colors['TCtemp']}),html.Td('Temperature TC'),html.Td(TCtemp['x'][-1].strftime("%H:%M:%S")),html.Td(format(TCtemp['y'][-1],'0.3'))],style=bgstyle)]+
            [html.Tr([html.Td(style={'backgroundColor':colors['RTDtemp']}),html.Td('Temperature RTD'),html.Td(RTDtemp['x'][-1].strftime("%H:%M:%S")),html.Td(format(RTDtemp['y'][-1],'0.3'))],style=bgstyle)]+#round(,1)
            [html.Tr([html.Td(style={'backgroundColor':colors['flow1']}),html.Td(flownames['flow1']),html.Td(flow1['x'][-1].strftime("%H:%M:%S")),html.Td(format(flow1['y'][-1],'0.2'))],style=bgstyle)]+
            [html.Tr([html.Td(style={'backgroundColor':colors['flow2']}),html.Td(flownames['flow2']),html.Td(flow2['x'][-1].strftime("%H:%M:%S")),html.Td(format(flow2['y'][-1],'0.2'))],style=bgstyle)]+
            [html.Tr([html.Td(style={'backgroundColor':colors['flow3']}),html.Td(flownames['flow3']),html.Td(flow3['x'][-1].strftime("%H:%M:%S")),html.Td(format(flow3['y'][-1],'0.2'))],style=bgstyle)]+
            [html.Tr([html.Td(style={'backgroundColor':colors['flow4']}),html.Td(flownames['flow4']),html.Td(flow4['x'][-1].strftime("%H:%M:%S")),html.Td(format(flow4['y'][-1],'0.2'))],style=bgstyle)]+
            [html.Tr([html.Td(style={'backgroundColor':colors['flow5']}),html.Td(flownames['flow5']),html.Td(flow5['x'][-1].strftime("%H:%M:%S")),html.Td(format(flow5['y'][-1],'0.2'))],style=bgstyle)]+
            [html.Tr([html.Td(style={'backgroundColor':colors['flow6']}),html.Td(flownames['flow6']),html.Td(flow6['x'][-1].strftime("%H:%M:%S")),html.Td(format(flow6['y'][-1],'0.2'))],style=bgstyle)]
            )
    return out




if __name__ == '__main__':
#    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#    sock.settimeout(1)
    app.run_server(host='0.0.0.0',debug=True,port=8050)
    



