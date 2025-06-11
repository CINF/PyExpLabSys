import time
import random
import datetime
import pyvisa as visa


class Keithley2450:
    def __init__(self, interface='lan', hostname=''):
        if interface == 'lan':
            visa_string = 'TCPIP0::{}::inst0::INSTR'.format(hostname)
        rm = visa.ResourceManager()
        self.instr = rm.open_resource(visa_string)

        # cmd = 'smu.measure.displaydigits = smu.DIGITS_6_5'
        # self.instr.write(cmd)

    def _cmd(self, cmd: str, query: bool, node: int = 0):
        if node == 0:
            n_str = 'localnode.'
        else:
            n_str = 'node[{}].'.format(node)
        node_cmd = cmd.replace('[]', n_str)
        # print('cmd: ', node_cmd)
        if query:
            reply = self.instr.query(node_cmd)
        else:
            reply = None
            self.instr.write(node_cmd)
        return reply

    def write(self, cmd, node=None):
        self._cmd(cmd=cmd, query=False, node=node)

    def query(self, cmd, node=None):
        reply = self._cmd(cmd, query=True, node=node)
        return reply

    def reset_instrument(self):
        """
        Send the reset comand to the instrument.
        """
        self.instr.write('reset()')
        time.sleep(0.5)

    def clear_output_queue(self):
        """
        I assume a more offical way to do this exists. For now this will do.
        """
        marker = '!' + str(random.random()) + '!'

        self.instr.write('print("{}")'.format(marker))
        script_ended = False
        while not script_ended:
            output = self.instr.read().strip()
            if output.find(marker) > -1:
                script_ended = True
        return

    def use_rear_terminals(self, use_rear: bool = True, node: int = 0):
        """
        If True (default), the instrument will use the recommended configuration
        of using the rear triax terminals. If False the front banana's are used.
        """
        if use_rear:
            cmd = '[]smu.measure.terminals = []smu.TERMINALS_REAR'
        else:
            cmd = '[]smu.measure.terminals = []smu.TERMINALS_FRONT'
        self.write(cmd, node)
        return use_rear

    def output_state(self, output_state: bool = None, node: int = 0):
        """
        Turn the output on or off
        """
        if output_state is not None:
            if output_state:
                cmd = '[]smu.source.output = []smu.ON'
            else:
                cmd = '[]smu.source.output = []smu.OFF'
            self.write(cmd, node)
        cmd = 'print([]smu.source.output)'
        actual_state_raw = self.query(cmd, node)
        actual_state = actual_state_raw.find('smu.ON') > -1
        return actual_state

    def set_current(self, current: float):
        """DEPRECATED: Here only for compatibility - will be removed"""
        print('k2450 - set-current is deprecated!')
        self.set_output_level(current)
        return True

    def set_voltage(self, voltage: float):
        """DEPRECATED: Here only for compatibility - will be removed"""
        print('k2450 - set-voltage is deprecated!')
        self.set_output_level(voltage)
        return True

    def set_output_level(self, level: float = None, node: int = 0):
        """
        Set the output level. If level is None, no changes
        are made, but the actual configured value is returned.
        Notice - this is not a measurement but the configured
        wanted output level.
        """
        if level is not None:
            cmd = '[]smu.source.level={}'.format(level)
            self.write(cmd, node)

        cmd = 'print([]smu.source.level)'
        actual = float(self.query(cmd, node))
        return actual

    def set_source_function(
        self, function: str = None, source_range: float = None, node: int = 0
    ):
        if function.lower() in ('i', 'current'):
            self.write('[]smu.source.func = []smu.FUNC_DC_CURRENT', node)
        if function.lower() in ('v', 'voltage'):
            self.write('[]smu.source.func = []smu.FUNC_DC_VOLTAGE', node)

        if source_range is not None:
            if source_range == 0:
                self.write('[]smu.source.autorange = []smu.ON', node)
            else:
                self.write('[]smu.source.autorange = []smu.OFF', node)
                self.write('[]smu.source.range = {}'.format(source_range), node)

        actual_function = self.query('print([]smu.source.func)', node)
        # TODO: PARSE THIS INTO ENUM OF VOLTAGE AND CURRENT
        return actual_function

    def set_readback(self, action: bool = None, node: int = 0):
        """
        Set readback behaviour.
        Action can be 'on', 'off', or None
        """
        if action is not None:
            if action:
                cmd = '[]smu.source.readback = []smu.ON'
            else:
                cmd = '[]smu.source.readback = []smu.OFF'
            self.write(cmd, node)

        cmd = 'print([]smu.source.readback)'
        actual_state_raw = self.query(cmd, node)
        actual_state = actual_state_raw.find('ON') > -1
        return actual_state

    def remote_sense(self, action: bool = None, node: int = 0):
        if action is not None:
            if action:
                self.write('[]smu.measure.sense = []smu.SENSE_4WIRE', node)
            else:
                self.write('[]smu.measure.sense = []smu.SENSE_2WIRE', node)
        actual_state = self.query('print([]smu.measure.sense)', node).find('4WIRE') > -1
        return actual_state

    def set_sense_function(
        self, function: str = None, sense_range: float = None, node: int = 0
    ):
        """
        Set the sense range, a value of None returns the current value without
        changing the actual value. A range value of 0 indicates auto-range.
        """
        # TODO:
        # Many other measurement functions exists, such as resistance, power
        # and math functions
        if function.lower() in ('i', 'current'):
            self.write('[]smu.measure.func = []smu.FUNC_DC_CURRENT', node)
        if function.lower() in ('v', 'voltage'):
            self.write('[]smu.measure.func = []smu.FUNC_DC_VOLTAGE', node)

        if sense_range == 0:
            self.write('[]smu.measure.autorange = []smu.ON', node)
        else:
            cmd = '[]smu.measure.range = {}'.format(sense_range)
            self.write(cmd, node)

        actual_function = self.query('print([]smu.measure.func)', node)
        # TODO: PARSE THIS INTO ENUM OF VOLTAGE AND CURRENT
        return actual_function

    def set_auto_zero(self, action: bool = None, node: int = 0):
        """
        Set auto-zero behaviour.
        Action can be 'on', 'off', or None
        """
        if action is not None:
            if action:
                cmd = '[]smu.measure.autozero.enable = []smu.ON'
            else:
                cmd = '[]smu.measure.autozero.enable = []smu.OFF'
            self.write(cmd, node)

        cmd = 'print([]smu.measure.autozero.enable)'
        actual_state_raw = self.query(cmd, node)
        actual_state = actual_state_raw.find('ON') > -1
        return actual_state

    def auto_zero_now(self, node: int = 0):
        """
        Perform a single auto-zero
        """
        self.write('[]smu.measure.autozero.once()', node)
        return True

    def set_limit(self, value: float, node: int = 0):
        """
        Set the desired limit for voltage or current depending on current
        source function.
        TODO: Query the measure range to check if value is legal
        """
        cmd = 'print([]smu.source.func)'
        source_func = self.query(cmd, node)
        if source_func.find('VOLTAGE') > -1:
            cmd = '[]smu.source.ilimit.level'
        else:
            cmd = '[]smu.source.vlimit.level'
        if value is not None:
            limit_cmd = cmd + '={}'.format(value)
            self.write(limit_cmd, node)
        return value

    # Compatibility function, could be removed
    def set_current_limit(self, current: float = None):
        cmd = 'smu.source.func = smu.FUNC_DC_VOLTAGE'
        self.instr.write(cmd, node)
        if current is not None:
            self.set_limit(value=current)
        return current

    def query_limit(self, node: int = 0):
        """
        Query the current source limit
        """
        query_cmd = 'print([]smu.source.ilimit.level)'
        print(query_cmd)
        limit = float(self.query(query_cmd, node))
        return limit

    def buffer_exists(self, buffer: str):
        """
        Todo: This is not yet compatible with TSP link
        """
        cmd = 'print({} == nil)'.format(buffer)
        buffer_exists = self.instr.query(cmd).strip() == 'false'
        return buffer_exists

    def make_buffer(self, buffer: str, size: int = 10):
        """
        Todo: This is not yet compatible with TSP link
        Make a buffer of type FULL and fillmode continous
        @return: True if created, false if buffer was already present
        """
        if size < 10:
            return False

        if self.buffer_exists(buffer):
            return False

        # TODO: Check if STYLE_FULL actually makes sense
        cmd = '{} = buffer.make({}, buffer.STYLE_FULL)'.format(buffer, size)
        self.instr.write(cmd)

        cmd = '{}.fillmode = buffer.FILL_CONTINUOUS'.format(buffer)
        self.instr.write(cmd)
        return True

    def set_integration_time(self, nplc: float = None, node: int = 0):
        """
        Set the measurement integration time
        In principle the current ant voltage value can be set
        independently, but for now they are synchronized
        """
        if nplc is not None:
            if nplc < 0.01:
                nplc = 0.01
            if nplc > 10:
                nplc = 10
            self.write('[]smu.measure.nplc = {}'.format(nplc), node)

        cmd = 'print([]smu.measure.nplc)'
        current_nplc = float(self.query(cmd, node))
        return current_nplc

    def trigger_measurement(self, buffer: str = 'defbuffer1', node: int = 0):
        cmd = 'print([]smu.measure.read({}))'.format(buffer)
        value = float(self.query(cmd, node))
        return value

    def clear_buffer(self, buffer: str = 'defbuffer1', node: int = 0):
        """
        TODO: This will quite likely fail for non-default buffers
        since, buffer_exsists is not yet tsp-link compatible
        """
        if not self.buffer_exists(buffer):
            return False
        cmd = '[]{}.clear()'.format(buffer)
        self.write(cmd, node)
        return True

    # def elements_in_buffer(self, buffer: str = 'defbuffer1'):

    def read_latest(self, buffer: str = 'defbuffer1'):
        reading = {}
        cmd = 'a={}; n = a.endindex'.format(buffer)
        self.instr.write(cmd, node)

        # Todo: bufferVar.statuses (manual 8-34)
        # Todo: bufferVar.sourcestatuses (manual 8-29)
        cmd = 'printbuffer(n, n, a, a.sourcevalues, a.timestamps)'
        raw = self.instr.query(cmd).strip().split(',')
        print(raw)
        reading['value'] = float(raw[0])
        reading['source_value'] = float(raw[1])
        reading['timestamp'] = datetime.datetime.strptime(
            raw[2].strip()[0:25], '%m/%d/%Y %H:%M:%S.%f'
        )
        return reading

    def load_script(self, name: str, script: str):
        """
        Load a script into non-volatile memory. Existing script with same
        name will be overwritten.
        The script should be formatted as a multi-line string that will be sent
        to the instrument line by line.
        """
        self.instr.write('script.delete("{}")'.format(name))

        self.instr.write('loadscript {}'.format(name))
        lines = script.split('\n')[1:-1]
        for line in lines:
            self.instr.write(line.strip())
        self.instr.write('endscript')
        self.instr.write('{}.save()'.format(name))

    def execute_script(self, name):
        self.instr.write('{}.run()'.format(name))

    def set_clock(self, node: int = 0):
        """
        Update the instrument clock to 'Now'
        :param node: If the value is not 0, the relevant node on the TSP-network
        is acticated rather han local node (default).
        """
        now = datetime.datetime.now()
        cmd = '[]settime({}, {}, {}, {}, {}, {})'.format(
            now.year, now.month, now.day, now.hour, now.minute, now.second
        )
        self.write(cmd, node)


if __name__ == '__main__':
    hostname = '192.168.0.3'
    k = Keithley2450(interface='lan', hostname=hostname)

    cmd = 'node[2].trigger.model.initiate()'
    k.instr.write(cmd)

    # k.instr.write('trigger.model.initiate()')
    exit()

    t = time.time()
    cmd = 'smu.source.sweeplinear("VoltLinSweep", 0, 1, 100, 1e-3, 1, smu.RANGE_FIXED)'
    # k.instr.write(cmd)
    # exit()

    t = time.time()
    for i in range(0, 100):
        print(k.trigger_measurement(node=1))
        level = i * 0.01
        k.set_output_level(level=level, node=1)
    print(time.time() - t)
    exit()

    # k.instr.write('node[2].smu.measure.nplc=1')
    # k.instr.write('node[2].smu.measure.autozero.enable = node[2].smu.OFF')

    # exit()

    # k.set_clock(2)

    k.instr.timeout = 1000

    N = 200
    script = """
    smu.measure.nplc=2
    smu.measure.autozero.enable = smu.OFF
    smu.source.readback = smu.OFF
    defbuffer1.clear()
    for i = 1, {} do
    smu.measure.read(defbuffer1)
    n = defbuffer1.endindex    
    printbuffer(n, n, defbuffer1, defbuffer1.sourcevalues, defbuffer1.timestamps)
    end
    print('end')
    """.format(
        N
    )

    script = """
    node[2].smu.measure.nplc=1
    node[2].smu.measure.autozero.enable = node[2].smu.OFF
    node[2].smu.source.readback = node[2].smu.OFF
    node[2].defbuffer1.clear()
    for i = 1, {} do
    node[2].smu.measure.read(defbuffer1)
    n = node[2].defbuffer1.endindex    
    printbuffer(n, n, node[2].defbuffer1, node[2].defbuffer1.sourcevalues, node[2].defbuffer1.timestamps)
    end
    print('end')
    """.format(
        N
    )

    script = """

    
    
    """

    k.load_script('test', script)
    k.execute_script('test')
    # time.sleep(1)
    output = k.instr.read().strip()
    output_start = output
    script_ended = False
    while not script_ended:
        output_end = output
        output = k.instr.read().strip()
        print(output)
        if output.find('end') > -1:
            script_ended = True

    print()
    t_start_raw = output_start.split(',')[2].strip()[0:25]
    t_end_raw = output_end.split(',')[2].strip()[0:25]

    t_start = datetime.datetime.strptime(t_start_raw, '%m/%d/%Y %H:%M:%S.%f')
    t_end = datetime.datetime.strptime(t_end_raw, '%m/%d/%Y %H:%M:%S.%f')

    print(t_start)
    print(t_end)
    dt = (t_end - t_start).total_seconds()
    msg = 'Total: {}s. Pr line: {}ms. NPLC = {:.1f}'
    print(msg.format(dt, 1000 * dt / N, 50.0 * dt / N))
