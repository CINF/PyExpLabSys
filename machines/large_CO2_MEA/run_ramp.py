# -*- coding: utf-8 -*-
"""
Created on Tue Feb 13 14:10:23 2018

@author: surfcat

Program for running voltage-current measurements and logging data to the database.

The input is given in form of a python file called ramp.py which contains the data about the experiment.

Example of  ramp file:

# Ports to connect to power supply and flow meters.
RED_FLOW_METER_COM_PORT = "COM4"
POWER_SUPPLY_COM_PORT = "COM6"

# Specify measurement type (This is data shown on the surfcat data site about themeasurement)
metadata = {
    'type': 14# The setup just has the reference 14,
    'comment': "Some comment about the measurement I am performing",
    'cathode_gas_type': "A gas Type",
    'anode_gas_type': "A gas type",
    'cathode_catalyst_description': "5 mg Ag/cm^2 size: 6.25cm2",  #  "The': 4cm2' is important for normalization!"
    'anode_catalyst_description': "Perforated nickel plate with carbon paper on the back 6.25cm2,
}
# Here you specify the steps in your program, it can have 1 or several steps.
RAMP = [
    {'type': 'constant_voltage', 'duration': 1, 'end_voltage': 2, 'save_rate': 1},  # This is one step
    {'type': 'voltage_ramp', 'duration': 600, 'start_voltage': 0, 'end_voltage': 5, 'voltage_step': 0.05, 'save_rate': 1}
]
"""

# Import general packages
from time import time, sleep
from serial import SerialException
import socket
import json

# Import drivers
from PyExpLabSys.drivers.vogtlin import RedFlowMeter
from PyExpLabSys.drivers.cpx400dp import CPX400DPDriver
from PyExpLabSys.common.database_saver import  DataSetSaver, CustomColumn

# Import credentials for database logging
import credentials


# Import data file
import ramp
#import testing_sequence as ramp

class RampRunner(object):
    """The RampRunner. Program to run current and voltage measurements and log measurements
    of voltage, current, temperature, pressure and flow to the surfcat database.    
    """

    def __init__(self):
        # Initialize power supply
        # Initialize flow meter driver
        """Try to connect to the COM port of the flow meter and ask for the serial number"""
        print("Try and connect to red flow meter")
        try:
            self.red_flow_meter = RedFlowMeter(ramp.RED_FLOW_METER_COM_PORT, slave_address=2)
        except SerialException:
            message = 'Cannot find red flow meter on {}'.format(ramp.RED_FLOW_METER_COM_PORT)
            raise RuntimeError(message) 
    
        # Test serial number reply
        if self.red_flow_meter.read_value('serial') != 181787:
            raise RuntimeError('Incorrect reply to serial number')
    
        # Print actual flow value
        print(self.red_flow_meter.read_value('fluid_name'), self.red_flow_meter.read_value('flow'))
        self.red_flow_meter.set_address(247)
        print(self.red_flow_meter.read_value('fluid_name'), self.red_flow_meter.read_value('flow'))
        
        # Try to conect to power supply 
        print("Try and connect to power supply")
        try:
            self.cpx = CPX400DPDriver(output=1, interface='serial', device=ramp.POWER_SUPPLY_COM_PORT)
        except SerialException:
            message = 'Cannot find power supply on {}'.format(ramp.POWER_SUPPLY_COM_PORT)
            raise RuntimeError(message)
    
        if 'CPX400DP' not in self.cpx.read_software_version():
            raise RuntimeError('Incorrect software version reply')
            pass
        
        # Print the set point voltage
        print("The voltage set point is {}".format(self.cpx.read_set_voltage()))
        
        self.ramp = ramp.RAMP
        self.metadata = ramp.metadata
        self.verify_ramp()
        self.data_set_saver = DataSetSaver(
            'measurements_large_CO2_MEA',
            'xy_values_large_CO2_MEA',
            credentials.USERNAME,
            credentials.PASSWORD,
        )
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.1)
        self.host = ramp.RASPPI_HOST
        self.port = ramp.RASSPI_PORT
        self.message = 'json_wn#' + json.dumps({'no_voltages_to_set':True})
        

    def verify_ramp(self):
        """Verify the ramp for consistency and safety"""        
        for step in self.ramp:
            
            # Check if a contant voltage step has the right keys
            if step['type'] == 'constant_voltage':
                required_keys = {'type','duration','end_voltage', 'save_rate'}
                if step.keys() != required_keys:
                    raise RuntimeError('The keys must in a constant voltage step must be\
                                       {}'.format(required_keys))
                    
            # Check if a voltage ramp step has the right keys     
            elif step['type'] == 'voltage_ramp':
                required_keys = {'type', 'duration',\
                                 'start_voltage', 'end_voltage', 'voltage_step', 'save_rate'}
                if step.keys() != required_keys:
                    raise RuntimeError('The keys must in a constant voltage step must be\
                                       {}'.format(required_keys))
                elif step['start_voltage'] < 0: 
                    raise RuntimeError('Voltage must be must be positive and less than 5V, got: {}V'\
                                   .format(step['end_voltage']))
                elif step['end_voltage'] > 5:
                    raise RuntimeError('Voltage must be must be positive and less than 5V, got: {}V'\
                                   .format(step['end_voltage']))
                    
            elif step['type'] == 'constant_current':
                required_keys = {'type', 'duration',\
                                 'current_density', 'save_rate','area'}
                if step.keys() != required_keys:
                    raise RuntimeError('The keys must in a constant voltage step must be\
                                       {}'.format(required_keys))
                elif step['current_density'] < 0: 
                    raise RuntimeError('Current density must be positive, got: {}mA/cm2'\
                                   .format(step['current_density']))
                elif step['area'] < 0:
                    raise RuntimeError('Area must be positive, got: {}cm2'\
                                   .format(step['area']))
            
            # Do checks on the common keys
            elif step['duration'] <= 0: 
                raise RuntimeError('Duration must be positive, got: {}'.format(step['duration']))
            # Check that the voltage is greater than 0 
            elif step['end_voltage'] < 0: 
                raise RuntimeError('Voltage must be must be positive and less than 5V, got: {}V'\
                                   .format(step['end_voltage']))
            #...and less than 5V
            elif step['end_voltage'] > 5:
                raise RuntimeError('Voltage must be must be positive and less than 5V, got: {}V'\
                                   .format(step['end_voltage']))
            # Check if the rate at which the data should be saved is positive.
            elif step['save_rate'] <=0:
                raise RuntimeError('The save rate must be positive, got: {}'.format(step['save_rate']))
            

    def run(self):
        """Run the ramp
        
        This is the main function that contains a loop over the steps in the ramp and the
        method that does all the work
        """
        
        self.data_set_saver.start()
        # Specify the start time for database
        now = time()
        now_custom_column = CustomColumn(now, 'FROM_UNIXTIME(%s)')
        
        # Add all measurements
        self.metadata['label'] = 'voltage'
        self.data_set_saver.add_measurement('voltage', self.metadata)
        self.metadata['label'] = 'current'
        self.data_set_saver.add_measurement('current', self.metadata)
        self.metadata['label'] = 'CO2 flow'
        self.data_set_saver.add_measurement('CO2 flow', self.metadata)
        # Add the one custom column
        self.metadata['time'] = now_custom_column
        
        # Set the current limit on the power supply to 10A
        self.cpx.set_current_limit(10)
        
        # Set the pressure on the pressure controller
        
        try:
            for step in self.ramp:
                # Go through the steps in the ramp file
                if step['type'] == 'constant_voltage':
                    self.run_constant_voltage_step(step)
                elif step['type'] == 'voltage_ramp':
                    self.run_voltage_ramp_step(step)
                elif step['type'] == 'constant_current':
                    self.run_constant_current_step(step)
        except KeyboardInterrupt:
            print('Program interupted by user')
            
        except IOError as e:
            print("I/O error({0}): {1}".format(e.errno, e.strerror))
            pass
        finally:
            # End the data collection and turn off power supply after run or interruption
            print('The program has ended')
            self.cpx.output_status(False)
            self.data_set_saver.wait_for_queue_to_empty()
            self.data_set_saver.stop()
        
        

    def run_constant_voltage_step(self, step):
        """Run a single step"""
        print('Run constant voltage step with parameters', step)
        start_time = time()  # Read from step
                
        # Set voltage on power supply
        voltage_difference_limit = 0.01
        print("Setting voltage to {} V".format(step["end_voltage"]))
        self.cpx.set_voltage(step["end_voltage"])
        while abs(step["end_voltage"]-self.cpx.read_set_voltage())>voltage_difference_limit:
            print(self.cpx.read_set_voltage())
            pass
        
        # Change address to CO2 flow meter
        self.red_flow_meter.set_address(247)
        # Turn on the power supply
        self.cpx.output_status(True)
        
        last_save = 0
        # Read of the flow and current as long as the duration lasts
        while (time() - start_time) < step['duration']*3600:
            # Log results to database
            
            # Send communication to datacard
            self.sock.sendto(self.message.encode('ascii'), (self.host, self.port))
            try:
                reply = self.sock.recv(1024).decode('ascii')
            except socket.timeout:
                pass
            else:
                # This is the data collection rate right now
                sleep(step['save_rate'])
                now = time()
                
                # Read voltage on power supply
                power_supply_voltage = self.cpx.read_actual_voltage()
                print('The voltage is: {}V on the power supply'.format(power_supply_voltage))
                
                # Read actual voltage on raspberry pi
                reply_data = json.loads(reply[4:])
                actual_voltage = reply_data['3']
                print('The voltage is: {}V on the cell'.format(actual_voltage))
            
                # Read the current from the power supply
                actual_current  = self.cpx.read_actual_current()
                print('The current is: {}A'.format(actual_current))
                
                
                # Get the CO2 flow from the MFM
                CO2_flow = self.red_flow_meter.read_value('flow')
                
                # time between data is saved
                print('Time since last save: {}s'.format(time()-last_save))
                last_save = time()
                
                # Save the measurements to the database
                self.data_set_saver.save_point('voltage', (now, actual_voltage))
                self.data_set_saver.save_point('current', (now, actual_current))
                self.data_set_saver.save_point('CO2 flow', (now, CO2_flow))
            
        
    def run_constant_current_step(self, step):
        """Run a single step"""
        print('Run constant current step with parameters', step)
        start_time = time()  # Read from step
        
        # Change address to CO2 flow meter
        self.red_flow_meter.set_address(247)
        # Set current limit on power supply and set a high voltage to hit the limit
        # and let the power supply control the voltage
        area = step['area'] # in cm2
        current_density = step['current_density'] # in mA
        # Calculte the area 
        current = current_density/1000*area
        print("Setting current to {}A".format(current))
        self.cpx.set_current_limit(current)
        self.cpx.set_voltage(4)
        # Turn on the power supply
        self.cpx.output_status(True)
        
        last_save = 0
        # Read of the flow and current as long as the duration lasts
        while (time() - start_time) < step['duration']*3600:
            # Log results to database
            
            # Send communication to datacard
            self.sock.sendto(self.message.encode('ascii'), (self.host, self.port))
            try:
                reply = self.sock.recv(1024).decode('ascii')
            except socket.timeout:
                pass
            else:
                # This is the data collection rate right now
                sleep(step['save_rate'])
                now = time()
                
                # Read voltage on power supply
                power_supply_voltage = self.cpx.read_actual_voltage()
                print('The voltage is: {}V on the power supply'.format(power_supply_voltage))
                
                # Read actual voltage on raspberry pi
                reply_data = json.loads(reply[4:])
                actual_voltage = reply_data['3']
                print('The voltage is: {}V on the cell'.format(actual_voltage))
            
                # Read the current from the power supply
                actual_current  = self.cpx.read_actual_current()
                print('The current is: {}A'.format(actual_current))
                
                
                # Get the CO2 flow from the MFM
                CO2_flow = self.red_flow_meter.read_value('flow')
                
                # time between data is saved
                print('Time since last save: {}s'.format(time()-last_save))
                last_save = time()
                
                # Save the measurements to the database
                self.data_set_saver.save_point('voltage', (now, actual_voltage))
                self.data_set_saver.save_point('current', (now, actual_current))
                self.data_set_saver.save_point('CO2 flow', (now, CO2_flow))


    def run_voltage_ramp_step(self, step):
        """ Run voltage ramp step"""
        print('Run voltage ramp step with parameters', step)
        # Start time of this step for reference
        start_time = time()
        
        # Set voltage to the start voltage in the step and turn on the voltage
        self.cpx.set_voltage(step['start_voltage'])
        print('Starting voltage ramp at: {}'.format(step['start_voltage']))
        self.cpx.output_status(True)
        
        
        voltage_set_point = step['start_voltage']
        
        
        while (time() - start_time) < step['duration']*3600:
            now = time()
            
            # Change address to CO2 flow meter
            self.red_flow_meter.set_address(247)
            # Read flow value
            CO2_flow = self.red_flow_meter.read_value('flow')
            print(self.red_flow_meter.read_value('fluid_name'), CO2_flow)
            
            # Change address to N2 flow meter
            self.red_flow_meter.set_address(2)
            # Read flow value
            N2_flow = self.red_flow_meter.read_value('flow')
            print(self.red_flow_meter.read_value('fluid_name'), N2_flow)
            
            # Set the voltage on the power supply
            self.cpx.set_voltage(voltage_set_point)
            
            # Read actual voltage
            actual_voltage = self.cpx.read_actual_voltage()
            print('The current voltage is: {}V'.format(actual_voltage))
            print('The voltage set point is {}V'.format(voltage_set_point))
            # Read the current from the power supply
            actual_current  = self.cpx.read_actual_current()
            print('The current current is: {}A'.format(actual_current))
            
            # This is the data collection rate right now
            sleep(step['save_rate'])
            # Save the measurements to the database
            self.data_set_saver.save_point('voltage', (now, actual_voltage))
            self.data_set_saver.save_point('current', (now, actual_current))
            self.data_set_saver.save_point('CO2 flow', (now, CO2_flow))
            # Ramp the voltage by the voltage step in step
            voltage_set_point = voltage_set_point + step['voltage_step']
            
            # Terminate the ramp when the end voltage is reached            
            if voltage_set_point >= step['end_voltage']:
                print('end voltage, {} reached'.format(step['end_voltage']))
                sleep(1)
                # Turn off the power supply
                #self.cpx.output_status(False)
                break
        
        # Tell when the time loop is done and turn of power supply
        print('voltage ramp step has ended')
        
            
ramp_runner = RampRunner()
ramp_runner.run()