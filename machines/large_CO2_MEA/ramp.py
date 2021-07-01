# -*- coding: utf-8 -*-
"""
Created on Tue Feb 13 14:39:49 2018

@author: surfcat
"""

# Template
# {'type': 'constant_voltage', 'duration': 8, 'end_voltage': 2, save_rate': 1}
# {'type': 'voltage_ramp', 'duration': 100# in hours, 'start_voltage': 0, 'end_voltage': 3, 'voltage_step': 0.1, save_rate': 1# in seconds}
# {'type': 'constant_current', 'duration': 1 (in hours), 'current_density': 100, 'save_rate': 5, 'area':4.34}

# Ports to connect to power supply and flow meters.
RED_FLOW_METER_COM_PORT = "COM8"
POWER_SUPPLY_COM_PORT = "COM6"

# Host and port to connect to raspberry pi
RASPPI_HOST = 'rasppi76'
RASSPI_PORT = 8500

# Specifiy the cathode area for the current density
area = 4.00
# Specify the gas flow 
setpoint_gas_flow = 10.0


# Specify measurement type
metadata = {
    'type': 14,
    'comment': "Test connections after gas and power was turned off\
    Cell with Ir02 anode 250 mum gasket, cathode is Ag membrane from Sterlitech and 50 mum gasket.",
    'cathode_gas_type': "CO2",
    'anode_gas_type': "~1400 ml Water with 0.1M KHCO3",
    'cathode_catalyst_description': "Ag membrane size: 4.34cm2",  #  "This is what it is made of: 4cm2"
    'anode_catalyst_description': "IrO2 from sustainiom",
}



RAMP = [
    #{'type': 'voltage_ramp', 'duration': 600, 'start_voltage': 0, 'end_voltage': 4.5, 'voltage_step': 0.05, 'save_rate': 1},    
    {'type': 'constant_voltage', 'duration': 3, 'end_voltage': 0, 'save_rate': 5},  # Duration:hours, save_rate:seconds
    #{'type': 'constant_current', 'duration': 0.08, 'current_density': 100, 'save_rate': 5, 'area':4.34},# Duration:hours, current_density:mA/cm2, save_rate:seconds, area:mA/cm2
    #{'type': 'constant_current', 'duration': 0.08, 'current_density': 200, 'save_rate': 5, 'area':4.34},# Duration:hours, current_density:mA/cm2, save_rate:seconds, area:mA/cm2
    #{'type': 'constant_current', 'duration': 20, 'current_density': 0, 'save_rate': 5, 'area':4.34}# Duration:hours, current_density:mA/cm2, save_rate:seconds, area:mA/cm2
]
