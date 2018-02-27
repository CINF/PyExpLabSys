#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=broad-except
"""CPX drivers server, for connecting with several CPX power supplies

This file is part of the Voltage Current Program

Copyright (C) 2016-2017 Kenneth Nielsen and Robert Jensen

The Voltage Current Ramp Program is free software: you can
redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software
Foundation, either version 3 of the License, or
(at your option) any later version.

The Voltage Current Ramp Program is distributed in the hope
that it will be useful, but WITHOUT ANY WARRANTY; without even
the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more
details.

You should have received a copy of the GNU General Public License
along with The CINF Data Presentation Website.  If not, see
<http://www.gnu.org/licenses/>.

"""

import os
from os import path
from time import sleep
import traceback

from PyExpLabSys.drivers.cpx400dp import CPX400DPDriver
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.utilities import get_logger

print('PSU running')

# Check server lock
THIS_DIR = path.dirname(path.realpath(__file__))
print(THIS_DIR)

LOCK_FILE = path.join(THIS_DIR, 'SERVER_LOCK')
if path.isfile(LOCK_FILE):
    MESSAGE = ('Server already running\n'
               '\n'
               'The server lock file "SERVER_LOCK" is in place, which indicates that '
               'the server is already running.\n'
               '\n'
               'If you know that it is not true, delete the lock file.')
    raise RuntimeError(MESSAGE)
# Lock to prevent multiple servers
with open(LOCK_FILE, 'w') as file_:
    pass


LOG = get_logger('H2O2 CPX Serv', level='debug', file_log=True, file_name='server.log',
                 file_backup_count=1, file_max_bytes=1048576)
STOP_SERVER = False


class CPXServer(object):
    """Server for CPX400DP power supplies"""

    def __init__(self, devices=None):
        """Initialize CPXServer

        Args:
            devices (dict): Mapping of power supply names (letters) to hostnames. E.g:
                {'A': '/dev/serial/by-id/usb-TTI_CPX400_Series_PSU_C2F95400-if00',
                 'B': '/dev/serial/by-id/usb-TTI_CPX400_Series_PSU_12345600-if00'}
        """
        if not devices:
            msg = '"devices" must be dict of power supply number to hostname, not: {}'
            raise ValueError(msg.format(devices))

        self.devices = devices
        self.cpxs = {}  # Plural of cpx??
        # Mapping of power supply name to driver
        for power_supply_name, device in devices.items():
            LOG.debug('Connect %s, %s', power_supply_name, device)
            if not isinstance(power_supply_name, str):
                msg = '"power_supply_name" in devices must be str, not: {}'
                raise ValueError(msg.format(type(power_supply_name)))
            # Init CPX400DP driver
            self.cpxs[power_supply_name] = CPX400DPDriver(
                1,  # will be overwritten anyway
                interface='serial',
                device=device,
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
            for _ in range(3):
                try:
                    print('Connect to CPS', cpx.read_actual_voltage())
                    break
                except TypeError:
                    message = "Connection error, waiting 3 sec and try again"
                    print(message)
                    LOG.error(message)
                    sleep(3)
            else:
                message = (
                    'Unable to connect to power supplies\n'
                    'Swich them off and on and wait 3min and try again'
                )
                LOG.critical(message)
                raise RuntimeError(message)

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
            LOG.exception("An error occured during execution of command on CPX")
            raise
        else:
            return out

    def reset_cpx(self, kwargs):
        """Reset a CPX"""
        # close old
        print('reset')
        power_supply_name = kwargs.get('power_supply')
        sleep(5)
        print('after sleep')

        device = self.devices[power_supply_name]
        LOG.info('Attempt to re-init cpx %s at hostname %s', power_supply_name, device)
        try:
            cpx = CPX400DPDriver(
                1,  # will be overwritten anyway
                interface='serial',
                device=device,
            )
            self.cpxs[power_supply_name] = cpx
        except Exception:
            LOG.exception('Exception during reinit of CPX')


def main():
    """Main function"""
    devices = {
        'A': '/dev/serial/by-id/usb-TTI_CPX400_Series_PSU_C2F95400-if00',
        #'A': '/dev/serial/by-id/usb-TTi_CPX_Series_PSU_467069-if00',
        #'B': '/dev/serial/by-id/usb-TTi_CPX_Series_PSU_477250-if00',
    }
    cpx_server = CPXServer(devices=devices)
    cpx_server.dps.start()
    print("Server ready")
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
finally:
    os.remove(LOCK_FILE)
