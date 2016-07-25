# -*- coding: utf-8 -*-
""""""

from time import sleep
import traceback

from PyExpLabSys.drivers.cpx400dp import CPX400DPDriver
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.utilities import get_logger

LOG = get_logger('H2O2 CPX Serv', level='debug')


class CPXServer(object):
    
    def __init__(self, device='COM4'):
        self.cpx = CPX400DPDriver(1, interface='serial', device=device)
        self.accepted_commands = {
            'set_voltage', 'read_set_voltage',
            'set_current_limit', 'read_current_limit',
            'read_actual_voltage', 'read_actual_current',
            'output_status', 'read_output_status'
        }
        self.accepted_outputs = {'1', '2'}
        if self.cpx.read_actual_voltage() < -999:
            error = 'Unable to connect to power supply on device {}'.format(device)
            raise RuntimeError(error)
            
        # Form data push socket for receiving commands
        self.dps = DataPushSocket('H2O2_ps_server', action='callback_direct',
                                  callback=self.handle_command)

    def handle_command(self, kwargs):
        """Call back function that will be called when a request is received"""
        print("##", kwargs)
        command = kwargs.get('command')
        if command not in self.accepted_commands:
            return 'ERROR: Invalid command: {}'.format(command)

        output = kwargs.get('output')
        if output not in self.accepted_outputs:
            return 'ERROR: Invalid output: {}'.format(output)
        self.cpx.output = output

        try:
            function = getattr(self.cpx, command)
            if 'arg' in kwargs:
                arg = kwargs.get('arg')
                out = function(arg)
            else:
                out = function()
        except Exception:
            error = (
                'ERROR: An unhandled exception accoured during callback.\n'
                'The traceback was:\n' + traceback.format_exc()
            )
            return error
        else:
            return out        


def main():
    cpx_server = CPXServer(device='COM4')
    cpx_server.dps.start()
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        cpx_server.dps.stop()
main()