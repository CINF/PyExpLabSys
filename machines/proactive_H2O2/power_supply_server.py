# -*- coding: utf-8 -*-
"""CPX drivers server, for connecting with several CPX power supplies"""

from time import sleep
import traceback

from PyExpLabSys.drivers.cpx400dp import CPX400DPDriver
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.utilities import get_logger

LOG = get_logger('H2O2 CPX Serv', level='debug', file_log=True, file_name='server.log',
                 file_backup_count=1, file_max_bytes=1048576)
STOP_SERVER = False

import logging
pels_logger = logging.getLogger('PyExpLabSys.common.sockets.PushUDPHandler')
pels_logger.setLevel(logging.INFO)


class CPXServer(object):

    def __init__(self, devices=None):
        """Initialize CPXServer

        Args:
            devices (dict): Mapping of power supply names (letters) to hostnames. E.g:
                {'A': 'HOSTNAME-PS1', 'B': 'HOSTNAME-PS2'}
        """
        if not devices:
            msg = '"devices" must be dict of power supply number to hostname, not: {}'
            raise ValueError(msg.format(devices))

        self.cpxs = {}  # Plural of cpx??
        # Mapping of global output channels to power supply local ones. I.e:
        # {output_channel (str):(ps_number (int), ps_output_channel (str))}
        for power_supply_name, hostname in devices.items():
            LOG.debug('Connect %s, %s', power_supply_name, hostname)
            if not isinstance(power_supply_name, str):
                msg = '"power_supply_name" in devices must be str, not: {}'
                raise ValueError(msg.format(type(power_supply_name)))
            # Init CPX400DP driver
            self.cpxs[power_supply_name] = CPX400DPDriver(
                1,  # will be overwritten anyway
                interface='lan',
                hostname=hostname,
                tcp_port=9221,
            )

        self.accepted_commands = {
            'set_voltage', 'read_set_voltage',
            'set_current_limit', 'read_current_limit',
            'read_actual_voltage', 'read_actual_current',
            'output_status', 'read_output_status'
        }
        self.valid_outputs = {'1', '2'}

        # Test connection
        for cpx_name, cpx in self.cpxs.items():
            if cpx.read_actual_voltage() < -999:
                error = 'Unable to connect to power supply "{}" with name "{}"'
                raise RuntimeError(error.format(cpx, cpx_name))
            
        # Form data push socket for receiving commands
        self.dps = DataPushSocket('H2O2_ps_server', action='callback_direct',
                                  callback=self.handle_command)

    def handle_command(self, kwargs):
        """Call back function that will be called when a request is received"""
        LOG.debug('Got command: %s', kwargs)
        command = kwargs.get('command')

        # Test if we asked it to stop
        if command == 'STOP':
            global STOP_SERVER
            STOP_SERVER = True
            return 'asked to stop'

        if command == 'PING':
            return 'PONG'

        if command not in self.accepted_commands:
            msg = 'ERROR: Invalid command: %s'
            LOG.error(msg, command)
            return msg % command

        while True:
            try:
                out = self.execute_command(kwargs, command)
            except Exception:
                LOG.exception('An error occured during execution of command')
                self.reset_cpx(kwargs)
                continue
            if isinstance(out, int) and out < -999:
                return 0.047
                LOG.error('Return value %s was less than -999. Probably com error', out)
                self.reset_cpx(kwargs)
                continue
            return out

    def execute_command(self, kwargs, command):
        """Execute a command"""
        power_supply_name = kwargs.get('power_supply')
        try:
            cpx = self.cpxs[power_supply_name]
        except KeyError:
            msg = 'ERROR: Invalid power supply name "%s". Valid ones are: %s'
            LOG.error(msg, power_supply_name, self.cpxs.keys())
            return msg % (power_supply_name, self.cpxs.keys())

        output = kwargs.get('output')
        if output not in self.valid_outputs:
            msg = 'ERROR: Invalid power supply output: "%s". Valid ones are: %s'
            LOG.error(msg, output, self.valid_outputs)
            return msg % (output, self.valid_outputs)

        cpx.output = output

        cmd_msg = 'Run command "%s" with arg "%s" on CPX "%s" output "%s" returned %s'

        try:
            function = getattr(cpx, command)
            if 'arg' in kwargs:
                arg = kwargs.get('arg')
                out = function(arg)
                LOG.debug(cmd_msg, command, arg, cpx.hostname, cpx.output, out)
            else:
                out = function()
                LOG.debug(cmd_msg, command, None, cpx.hostname, cpx.output, out)
        except Exception:
            error = (
                'ERROR: An unhandled exception accoured during callback.\n'
                'The traceback was:\n' + traceback.format_exc()
            )
            LOG.exception("An error occured during execution of command on CPX")
            return error
        else:
            return out

    def reset_cpx(self, kwargs):
        """Reset a CPX"""
        # close old
        power_supply_name = kwargs.get('power_supply')
        sleep(10)
        print('after sleep')

        hostname = self.devices[power_supply_name]
        LOG.info('Attempt to re-init cpx %s at hostname %s', power_supply_name, hostname)
        try:
            cpx = CPX400DPDriver(
                1,  # will be overwritten anyway
                interface='lan',
                hostname=hostname,
                tcp_port=9221,
            )
            self.cpxs[power_supply_name] = cpx
        except Exception:
            LOG.exception('Exception during reinit of CPX')


def main():
    devices = {
        'A': 'SURFCAT-PROACTIVE-PS1',
        'B': 'SURFCAT-PROACTIVE-PS2',
        #'C': 'SURFCAT-PROACTIVE-PS3',
    }
    cpx_server = CPXServer(devices=devices)
    cpx_server.dps.start()
    try:
        while not STOP_SERVER:
            sleep(1)
    except KeyboardInterrupt:
        cpx_server.dps.stop()


try:
    main()
except:
    LOG.exception('Exception in program')
    raise