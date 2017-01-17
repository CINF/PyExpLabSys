
"""Web app for the magnificient bakeout app"""


import json
import os
from pprint import pprint
import socket
import requests
from flask import Flask, url_for, render_template

# Form app
app = Flask(__name__)
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

# Form UDP socket for sending commands to the bakeout app
SOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
HOSTNAME = os.environ["MACHINE"]
print(HOSTNAME)

"""
Socket (None) >>> set rasppi23:8500
Connected to: rasppi23:8500

The name of the socket is: thetaprobe-ec-extension-push_control

== Known commands ==

 * json_wn#
 * raw_wn#
 * name
 * status
 * commands

Socket (rasppi23:8500) >>> json_wn#{"1": 0.2}
"ACK#{u'1': 0.2}"
Socket (rasppi23:8500) >>> json_wn#{"1": 1}
"ACK#{u'1': 1}"
Socket (rasppi23:8500) >>> json_wn#{"1": 0.1}
"ACK#{u'1': 0.1}"

"""

@app.route('/')
def frontpage():
    """Produce the frontpage"""
    json_input = {}

    row_elements = [
        # Rows of id prefix, row title and element
        ('state{}', 'Current state', '<div class="circle" id="led{channel_number}"></div>'),
        ('current_value{}', 'Current setpoint', 'N/A'),
        ('requested_value{}', 'Change setpoint',
         '<input onchange="set_channel({channel_number})" id="input{channel_number}" '
         'type="number" step="0.05" min="0" max="1">'),
    ]
    
    return render_template('frontpage.html', row_elements=row_elements, json_input=json_input)


@app.route('/set/<request_parameters_string>')
def set(request_parameters_string):
    """Page to set parameters on the bakeout box"""
    print("Send set request", request_parameters_string)
    SOCKET.sendto(b"json_wn#" + request_parameters_string.encode('ascii'), (HOSTNAME, 8500))
    reply = SOCKET.recv(1024)
    print("Got reply", reply)
    # We return just the channel name
    return list(json.loads(request_parameters_string).keys())[0]


@app.route('/get/<channel_number>')
def get_channel(channel_number):
    """Page to get parameters from the bakeout box"""
    if channel_number == "all":
        SOCKET.sendto(b"json_wn", (HOSTNAME, 9000))
    else:
        SOCKET.sendto(channel_number.encode("ascii") + b"#json", (HOSTNAME, 9000))
    reply = SOCKET.recv(1024).decode('ascii')

    if channel_number != "all":
        data = json.loads(reply)
        data.append(channel_number)
        reply = json.dumps(data)
    return reply
