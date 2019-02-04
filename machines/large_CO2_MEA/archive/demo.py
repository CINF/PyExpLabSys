# -*- coding: utf-8 -*-
"""
Created on Tue Feb 13 14:07:55 2018

@author: surfcat
"""

from time import sleep

from serial import SerialException

from PyExpLabSys.drivers.vogtlin import RedFlowMeter
from PyExpLabSys.drivers.cpx400dp import CPX400DPDriver

RED_FLOW_METER_COM_PORT = "COM4"
POWER_SUPPLY_COM_PORT = "COM6"


class ClassDemo(object):
    def __init__(self):
        self.a = 8


def test_class_demo():
    print_demo = ClassDemo()
    print_demo.write_a()



def hardware_demo():
    """Demonstrate the flow meter driver"""
    # Try and connect
    print("Try and connect to red flow meter")
    try:
        red_flow_meter = RedFlowMeter(RED_FLOW_METER_COM_PORT, slave_address=2)
    except SerialException:
        message = 'Cannot find red flow meter on {}'.format(RED_FLOW_METER_COM_PORT)
        raise RuntimeError(message)

    # Test serial number reply
    if red_flow_meter.read_value('serial') != 181787:
        raise RuntimeError('Incorrect reply to serial number')

    # Print actual flow value
    print(red_flow_meter.read_value('fluid_name'), red_flow_meter.read_value('flow'))
    red_flow_meter.set_address(247)
    print(red_flow_meter.read_value('fluid_name'), red_flow_meter.read_value('flow'))
    print()


    # Power supply demo
    print("Try and connect to power supply")
    try:
        cpx = CPX400DPDriver(output=1, interface='serial', device=POWER_SUPPLY_COM_PORT)
        print("Success")
    except SerialException:
        message = 'Cannot find power supply on {}'.format(POWER_SUPPLY_COM_PORT)
        raise RuntimeError(message)

    if 'CPX400DP' not in cpx.read_software_version():
        raise RuntimeError('Incorrect software version reply')

    print("Voltage on channel 1")
    print(cpx.read_actual_voltage())
    cpx.set_voltage(0)
    cpx.set_current_limit(1)
    cpx.output_status(True)
    cpx.set_voltage(1)
    sleep(4)
    cpx.set_voltage(0)
    cpx.set_current_limit(0)
    cpx.output_status(False)

    # Change channel
    cpx.output = "2"
    print("Voltage on channel 2")
    print(cpx.read_actual_voltage())






#flow_meter_demo()
#power_supply_demo()
    
hardware_demo()