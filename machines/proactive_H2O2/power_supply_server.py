# -*- coding: utf-8 -*-
"""CPX drivers server, for connecting with several CPX power supplies"""

from time import sleep
import traceback

from PyExpLabSys.drivers.cpx400dp import CPX400DPDriver
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.utilities import get_logger

LOG = get_logger('H2O2 CPX Serv', level='debug', file_log=True, file_name='server.log')
STOP_SERVER = False


class CPXServer(object):

    def __init__(self, devices=None):
        """Initialize CPXServer

        Args:
            devices (dict): Mapping of power supply numbers to hostnames. E.g:
                {1: 'HOSTNAME-PS1', 2: 'HOSTNAME-PS2'}
        """
        if not devices:
            msg = '"devices" must be dict of power supply number to hostname, not: {}'
            raise ValueError(msg.format(devices))

        self.cpxs = {}  # Plural of cpx??
        # Mapping of global output channels to power supply local ones. I.e:
        # {output_channel (str):(ps_number (int), ps_output_channel (str))}
        self.output_channel_to_ps_channel = {}
        for power_supply_number, hostname in devices.items():
            LOG.debug('Connect %s, %s', power_supply_number, hostname)
            if not isinstance(power_supply_number, int):
                msg = '"power_supply_number" in devices must be int, not: {}'
                raise ValueError(msg.format(type(power_supply_number)))
            # Init CPX400DP driver
            self.cpxs[power_supply_number] = CPX400DPDriver(
                1,  # will be overwritte anyway
                interface='lan',
                hostname=hostname,
                tcp_port=9221,
            )
            # FIXME ADD
            self.output_channel_to_ps_channel[str(power_supply_number * 2 - 1)] = \
                (power_supply_number, "1")
            self.output_channel_to_ps_channel[str(power_supply_number * 2)] = \
                (power_supply_number, "2")
        self.accepted_commands = {
            'set_voltage', 'read_set_voltage',
            'set_current_limit', 'read_current_limit',
            'read_actual_voltage', 'read_actual_current',
            'output_status', 'read_output_status'
        }
        # Test connection
        for cpx in self.cpxs.values():
            if cpx.read_actual_voltage() < -999:
                error = 'Unable to connect to power supply on device {}'.format(cpx)
                raise RuntimeError(error)
            
        # Form data push socket for receiving commands
        self.dps = DataPushSocket('H2O2_ps_server', action='callback_direct',
                                  callback=self.handle_command)

    def handle_command(self, kwargs):
        """Call back function that will be called when a request is received"""
        print("##", kwargs)
        command = kwargs.get('command')

        # Test if we asked it to stop
        if command == 'STOP':
            global STOP_SERVER
            STOP_SERVER = True
            return 'asked to stop'

        if command == 'PING':
            return 'PONG'

        if command not in self.accepted_commands:
            return 'ERROR: Invalid command: {}'.format(command)

        output = kwargs.get('output')
        if output not in self.output_channel_to_ps_channel:
            return 'ERROR: Invalid output: {}'.format(output)

        power_supply = int(kwargs.get('power_supply'))
        cpx = self.cpxs[power_supply]
        cpx.output = output

        try:
            function = getattr(cpx, command)
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
    devices = {
        1: 'SURFCAT-PROACTIVE-PS1',
        2: 'SURFCAT-PROACTIVE-PS2',
    }
    cpx_server = CPXServer(devices=devices)
    cpx_server.dps.start()
    try:
        while not STOP_SERVER:
            sleep(1)
    except KeyboardInterrupt:
        cpx_server.dps.stop()


main()