import serial

from typing import Optional


class TdkLambdaZ(object):
    def __init__(self, device: str = '/dev/ttyACM0'):
        self.ser = serial.Serial(device, 9600, stopbits=1, timeout=2)

    def _comm(self, command: str) -> str:
        command = command + '\r'
        self.ser.write(command.encode('ascii'))
        return_string = ''.encode('ascii')
        while True:
            next_char = self.ser.read(1)
            if ord(next_char) == 13:
                break
            return_string += next_char
        decoded = return_string.decode()
        return decoded

    def read_temperature(self) -> float:
        # Here to match API of XP Power
        return 0.0

    def read_actual_voltage(self) -> float:
        # Here to match API of XP Power
        return self.voltage()

    def read_actual_current(self) -> float:
        # Here to match API of XP Power
        return self.current()

    def set_voltage(self, voltage: float) -> None:
        # Here to match API of XP Power
        self.voltage(voltage)

    def set_current(self, current: float) -> None:
        # Here to match API of XP Power
        self.current(current)

    def test_connection(self):
        reply = self._comm('ADR 01')
        print(reply)

    def remote_state(self, local: bool = False, remote: bool = False) -> str:
        """
        Query or set the remote state. If both local and remote is False
        the current state will be replied with no modifications.
        Return values can be REM or LOC.
        """
        command = None
        if local and remote:
            pass
        elif local:
            command = 'RMT LOC'
        elif remote:
            command = 'RMT REM'
        # Also a Local Lockout mode exists, this is not implemented
        if command is not None:
            self._comm(command)

        reply = self._comm('RMT?')
        return reply

    def _read_float(self, command: str) -> float:
        attempts = 0
        while -1 < attempts < 10:
            try:
                actual_string = self._comm(command)
                actual_value = float(actual_string)
                attempts = -1
            except ValueError:
                attempts += 1
            except Exception:
                attempts += 1

        if attempts > 0:
            raise Exception
        return actual_value

    def voltage(self, value: Optional[float] = None) -> float:
        if value is not None:
            command = 'PV {:.3f}'.format(value)
            print(self._comm(command))
        actual_voltage = self._read_float('MV?')
        return actual_voltage

    def voltage_protection(self, value: Optional[float] = None) -> float:
        if value is not None:
            command = 'OVP {:.3f}'.format(value)
            print(self._comm(command))
        actual_protection_voltage = self._read_float('OVP?')
        return actual_protection_voltage

    def current(self, value: Optional[float] = None) -> float:
        if value is not None:
            command = 'PC {:.3f}'.format(value)
            print(self._comm(command))
        actual_current = self._read_float('MC?')
        return actual_current

    def output_state(self, on: bool = False, off: bool = False) -> bool:
        command = None
        if on and off:
            pass
        elif on:
            command = 'OUT ON'
        elif off:
            command = 'OUT OFF'

        if command is not None:
            self._comm(command)
        reply = self._comm('OUT?')
        state = reply == 'ON'
        return state


if __name__ == '__main__':
    tdk = TdkLambdaZ()
    tdk.test_connection()
    print('Remote state: {}'.format(tdk.remote_state(remote=True)))
    print('Output state: {}'.format(tdk.output_state(on=True)))
    print('Voltage proction level: {}'.format(tdk.voltage_protection(5)))
    print()

    print(tdk.current(0.2))
    print(tdk.voltage(0.2))
