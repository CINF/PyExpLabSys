
import json
from pprint import pprint

import requests

from flask import Flask, url_for, render_template
app = Flask(__name__)
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True



@app.route('/')
def frontpage():
    """Produce the frontpage"""
    json_input = {
        'get_url': url_for('get', _external=True, request_parameters_string=json.dumps({'action': 'read', 'channel': 8})),
        'another': 8,
    }

    row_elements = [
        # Rows of id prefix, row title and element
        ('state{}', 'Current state', '<div class="circle" id="led{channel_number}"></div>'),
        ('current_value{}', 'Current setpoint', 'N/A'),
        ('requested_value{}', 'Setpoint', 'N/A'),
    ]
    
    return render_template('frontpage.html', row_elements=row_elements, json_input=json_input)


@app.route('/set/<request_parameters_string>')
def set(request_parameters_string):
    """Page to set parameters on the bakeout box"""
    parameters = json.loads(request_parameters_string)
    pprint(parameters)
    return str(parameters)


@app.route('/get/<request_parameters_string>')
def get(request_parameters_string):
    """Page to get parameters from the bakeout box"""
    parameters = json.loads(request_parameters_string)
    pprint(parameters)
    return str(parameters)
