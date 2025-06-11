"""
Simple driver for Keithley 2100 DMM
"""
import pyvisa as visa


class Keithley2100:
    """
    Simple driver for Keithley 2100 DMM
    Much of this code should also work on a model 2000, but I do not have
    one readily available.
    """

    def __init__(self, visa_string=None):
        rm = visa.ResourceManager()
        self.instr = rm.open_resource(visa_string)
        self.instr.timeout = 6000

    def reset(self):
        """
        Reset most function of the instrument. This wil not clear the
        error queue.
        """
        self.instr.write('*RST')

    def clear_errors(self):
        """
        Clear the error queue
        """
        self.instr.write('*CLS')

    def measurement_function(self, measurement_type: str = None) -> str:
        """
        TODO: Consider to turn measurement type into an enum.
        """
        if measurement_type is not None:
            cmd = 'SENSE:FUNCTION "{}"'.format(measurement_type)
            print(cmd)
            self.instr.write(cmd)
        actual_type = self.instr.query('SENSE:FUNCTION?')
        return actual_type

    def measurement_range(self, meas_range: float = None) -> float:
        """
        todo: Read the actual function and set range function accordingly
        - for now VOLT:DC is always used... easy to change when needed.
        """
        if meas_range is not None:
            if meas_range == 0:
                cmd = 'SENSE:VOLTAGE:DC:RANGE:AUTO ON'
            else:
                cmd = 'SENSE:VOLTAGE:DC:RANGE {}'.format(meas_range)
            self.instr.write(cmd)
        actual_range = self.instr.query('SENSE:VOLTAGE:DC:RANGE?')
        return actual_range

    def integration_time(self, nplc: float = None) -> float:
        """
        Set and/or read the measurement integration time in NPLCs.
        Notice, that the only actual values are 0.02, 0.1, 1 and 10
        For now only DC voltage is supported.
        """
        # Here we can also handle other measurement modes - later
        set_msg = 'SENSE:VOLTAGE:DC:NPLCYCLES {}'
        read_msg = 'SENSE:VOLTAGE:DC:NPLCYCLES?'

        if nplc is not None:
            if nplc < 0.02:
                nplc = 0.02
            if nplc > 10:
                nplc = 10
            self.instr.write(set_msg.format(nplc))
        current_nplc = float(self.instr.query(read_msg))
        return current_nplc

    def auto_zero(self, auto_zero: bool = None) -> bool:
        """
        The instrument both has a concept of auto-zero and auto-gain.
        From reading the manual for 4.5s, the difference in not entirely
        clear, for now both are turned on and off at the same time.

        Setting this function to False while already False will make
        the instrument perform a single auto-zero reading.
        """
        if auto_zero is not None:
            if auto_zero:
                self.instr.write('SENSE:ZERO:AUTO ON')
                self.instr.write('SENSE:GAIN:AUTO ON')
            else:
                self.instr.write('SENSE:ZERO:AUTO ONCE')
                self.instr.write('SENSE:GAIN:AUTO ONCE')

        actual = self.instr.query('SENSE:ZERO:AUTO?')
        actual_autozero = '1' in actual
        return actual_autozero

    def trigger_source(self, external: bool = None) -> bool:
        """
        Set the trigger source either to external or immediate.
        """
        if external is not None:
            if external:
                self.instr.write('TRIGGER:SOURCE External')
            else:
                self.instr.write('TRIGGER:SOURCE Immediate')

        actual = self.instr.query('TRIGGER:SOURCE?')
        actual_external = 'EXT' in actual
        return actual_external

    def read(self) -> float:
        value_raw = None
        try:
            value_raw = self.instr.query('READ?').strip()
        except visa.errors.VisaIOError:
            print('Timeout')

        try:
            value = float(value_raw)
        except ValueError:
            value = -99
        return value


if __name__ == '__main__':
    import time

    visa_string = 'USB0::1510::8448::8019151::0::INSTR'
    DMM = Keithley2100(visa_string=visa_string)

    DMM.measurement_function('volt:dc')
    DMM.measurement_range(0)
    time.sleep(1)
    print(DMM.read())
