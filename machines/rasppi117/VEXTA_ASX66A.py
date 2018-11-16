import sys
import time
import serial
import threading

from PyExpLabSys.common.supported_versions import python3_only
python3_only(__file__)


__VERSION__ = 'April 11, 2018'
# New:
#  - ZY_raster_pattern changed to its own threaded class
__AUTHOR__ = 'Jakob Ejler Soerensen'

def get_str_output(string):
    """From a line of string output, get the answer after the equality sign."""
    output = string.split('=')[1]
    output = output.split(' ')[0]
    #print(repr(output))
    return output

class VEXTA(object):
    """Basic device driver for communicating with VEXTA ASX66A motor via RS232"""

    def __init__(self, # pylint: disable=too-many-arguments
            port='/dev/ttyUSB0',
            baudrate=9600,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            maxpos=325.,
            minpos=25.,
            user_unit='mm',
            dist_per_rev=1,
            eol='\r\n',
        ):
        """Initialize object variables

        """

        # Open a serial connection to port
        self.eot = b'>' # End-of-transmission character
        timeout_counter = 0
        while timeout_counter < 10:
            timeout_counter += 1
            self.ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                parity=parity,
                stopbits=stopbits,
                bytesize=bytesize,
                timeout=0.025,
            )
            time.sleep(1)
            try:
                if self.ser.isOpen():
                    self.ser.eol = eol
                    break
            except AttributeError:
                print('Attemp #{}\n'.format(timeout_counter))
        else:
            print('Connection timeout')
            sys.exit()

        # User constants
        self.position = -9999
        self.query('pc {}'.format(self.position))
        self.maxpos = maxpos
        self.minpos = minpos
        self.query('UU ' + user_unit)
        self.abort = False
        self.move_error = False
        self.error_msg = []

        # Default values
        self.default_vr = 1.0   # running velocity
        self.query('vr {}'.format(self.default_vr))
        self.dis = 1.0  # distance per step
        self.query('dis {}'.format(self.dis))

    def _write(self, command):
        """WRITE ME"""

        byte_command = command + self.ser.eol
        self.ser.write(byte_command.encode())

    def _flush(self):
        """Flush input buffer"""
        print(self.ser.read(self.ser.inWaiting()))
        return

    def read_all(self):
        """WRITE ME"""

        return self.ser.readlines()

    def read(self, twait=0.010):
        """Read output from device"""
        output = b''
        timeout = 1.0
        time.sleep(0.020)
        t0 = time.time()
        while True:
            print(self.ser.inWaiting())
            if time.time()-t0 > timeout:
                print('Timeout')
                print(output.decode('ascii'))
                break
            elif self.ser.inWaiting() > 0:
                string = self.ser.read(self.ser.inWaiting())
                #print()
                #print(string.decode('ascii'))
                #print()
                output += string
                if self.eot in string:
                    return output
            else:
                time.sleep(twait)
            

    def query(self, command, output=None, debug=False, reader=0):
        """Query a command.
        Will currently also set values if given after the command. Differing from the write function,
        query however also displays the result.
        If output is not None, the value from the command will be returned in the form given by output.

        command (string): command to be sent to device
        output (type): None (default), str, bool, float, int
        """

        t0 = time.time()
        if not output in [str, bool, float, int, None, 'raw']:
            message = '\'output\' must be one of following: str, bool, float, int, None (default)'
            print(time.time() - t0)
            raise TypeError(message)
        #print('Writing command: ' + repr(command))
        self._write(command)

        # Get response
        #if output is None:
        #    return
        if reader == 0:
            response = self.read_all()
        elif reader == 1:
            response = self.read()
        else:
            self._flush()
        error = [x.decode().rstrip('\r\n').lstrip() for x in response if 'error' in x.decode().lower()]
        if output == 'raw':
            new_response = []
            for line in response:
                new_response.append(line.decode())
            print('Raw COMM time: {}'.format(time.time() - t0))
            return new_response
        response = [x.decode().rstrip('\r\n') for x in response if '=' in x.decode()]
        if len(error) == 0:
            for line in response:
                if debug:
                    print(line)
            if output == bool:
                print(time.time() - t0)
                return output(int(get_str_output(line)))
            elif output:
                print(time.time() - t0)
                return output(get_str_output(line))
        else:
            for line in error:
                print(line)

    def stop(self):
        """Close down unit properly."""
        self.ser.close()

    # Common functions used in raster/move function

    def move(self, x):
        """Move device to position x (absolute value)
        Returns True if new position is within allowed limits, False otherwise"""

        new_x, error = self.verify_x(x, mode='abs')
        if not error:
            self.query('ma ' + str(new_x))
            self.move_error = False
            return True
        else:
            self.move_error = True
            self.error_msg.append('ABS_FAIL: Failed in moving to position {}'.format(x))
            return False
        #    print('x value ({}) not between defined limits {},{}'.format(x, self.minpos, self.maxpos))

    def increment(self, x):
        """Move device an increment x.
        Returns True if new position is within allowed limits, False otherwise.

        Note: there is also >MI command used alongside >DIS"""
        new_x, error = self.verify_x(x, mode='inc')
        if not error:
            self.query('ma ' + str(new_x))
            self.move_error = False
            return True
        else:
            self.move_error = True
            self.error_msg.append('INC_FAIL: Failed in moving to position {}'.format(x))
            return False

    def get_position(self, position=True):
        """Ask device to return current position"""

        x = self.query('pc', output=float)
        if position:
            self.position = x
        return x

    def set_position(self, x):
        self.query('pc {}'.format(x))
        self.position = x

    def get_running_velocity(self):
        return self.query('vr', output=float)

    def set_running_velocity(self, vr):
        return self.query('vr {}'.format(vr))

    def get_distance_per_revolution(self):
        """Read DPR in order to distinguish between motor Z and Y """
        response = self.query('dpr', output='raw')
        part_response = response[1].rstrip('\r\n').split('=')[1]
        dpr_now, rest_string = part_response.split('(')
        dpr_set, unit = rest_string.split(') ')
        if dpr_now != dpr_set:
            raise IOError('Settings changed but not saved on loaded motor')
        return dpr_now, unit

    def escape(self):
        """<ESC> command. Abort current motion/sequence."""

        self._write(chr(27))

    def run_motion(self, x):
        """FIX ME... Meant as a sequence as motions"""
        self.increment(x)
        while True:
            break#signal = self.

    def is_running(self):
        """Query device whether a motion is still running"""
        return self.query('sigmove', output=bool, debug=False)

    def wait_for_motion(self, numpad=None):
        """Pause until end of motion"""
        self.abort = False # Allow for external signal (numpad) to abort motion
        try:
            while not self.abort:
                if self.is_running():
                    pass
                else:
                    print('Finished moving!')
                    self.get_position()
                    return True
            else:
                self.escape()
                self.get_position()
                return False
        except KeyboardInterrupt:
            self.escape()
            time.sleep(0.1)
            self.get_position()
            return False

    def verify_x(self, x, mode='inc'):
        """Check an x input versus the limits and return corrected value"""
        # 225 ms +- 5 ms
        
        t0 = time.time()
        # Get current position
        x_now = self.query('pc', output=float)
        error = False

        # Correct value to absolute number
        if mode == 'inc':
            x_new = x_now + x
        elif mode == 'abs':
            x_new = x

        # Round to third digit to ensure compatibility with precision of motor
        x_new = round(x_new, 3)

        # Return if within defined limits
        if x_now < self.minpos or x_now > self.maxpos:
            error = True
            print('Outside defined limits! Current position: {} [{},{}]'.format(x_now, self.minpos, self.maxpos))
            print('Time lapse for verify_x: {} s'.format(time.time()-t0))
            return x_new, error

        # Check limits
        if x_new > self.maxpos:
            x_new = self.maxpos
            error = True
        elif x_new < self.minpos:
            x_new = self.minpos
            error = True

        # Error found
        if error:
            if mode == 'inc':
                print('Too large step!\nPos now: {}\nPos after: {}\nLimit: [{},{}]'.format(x_now, x_now + x, self.minpos, self.maxpos))

        # Return
        print('Time lapse for verify_x: {} s'.format(time.time()-t0))
        return x_new, error

       

def connect_Z_Y(mdriver=VEXTA):
    """Connect both motors"""
    import platform
    import serial.tools.list_ports
    from serial.serialutil import SerialException

    system = platform.system()
    

    # Get a list of available USB ports
    list_of_ports = serial.tools.list_ports.comports()
    counter = 0
    Z, Y = None, None

    # Go through list to connect motor Z
    for port in list_of_ports:
        try:
            Z = mdriver(port=port.device)
            dpr, unit = Z.get_distance_per_revolution()

            # Verify that device is motor Z
            if dpr + unit == '2mm':
                print('Connected to Z.')
                list_of_ports.pop(counter)
                break

            # In case motor Y was encountered instead...
            elif dpr + unit == '1mm':
                Z.stop()
                time.sleep(1)
                Y = mdriver(port=port.device)
                print('Connected to Y.')
                counter += 1
                continue
        except SerialException:
            pass
        except IndexError:
            Z.ser.close()
        counter += 1
    else:
        Z = None
        print('Z motor not detected.')

    # Y was not encountered in previous loop
    if not Y:
        for port in list_of_ports:
            try:
                Y = mdriver(port=port.device)
                dpr, unit = Y.get_distance_per_revolution()
                if dpr + unit == '1mm':
                    print('Connected to Y.')
                    break
            except SerialException:
                pass
            except IndexError:
                Y.ser.close()
        else:
            print('Y motor not detected.')
            Y = None
    if Z:
        Z.minpos = 25
        Z.maxpos = 325
    if Y:
        Y.minpos = 42.5
        Y.maxpos = 65
    return Z, Y

class ZY_raster_pattern(threading.Thread):
    """Function to load and execute raster patterns"""

    def __init__(self, pattern_name, Z=None, Y=None):
        #
        # Initialize Thread
        #super(ZY_raster_pattern,self).__init__()
        super().__init__()

        # Load pattern and motors
        from simulate_pattern import load_pattern
        self.pattern_name = pattern_name
        self.pattern, self.data = load_pattern(pattern_name)
        
        if not Z or not Y:
            raise ValueError('Z or Y not provided')
        self.motor = {'Z': Z,
                      'Y': Y}

        # Attributes
        self.pos = {'Z': Z.get_position(),
                      'Y': Y.get_position()}
        self.vr = {'Z': Z.get_running_velocity(),
                   'Y': Y.get_running_velocity()}
        self.running = False
        self.status = ''
        self.logname = 'raster.log'
        f = open(self.logname, 'w')
        f.write('Log for rastering created {}\r\n'.format(time.asctime()))
        f.write('Raster file: {}\r\n'.format(pattern_name))
        f.write(str(self.data) + '\r\n')
        f.write(str(self.pattern) + '\r\n')
        f.close()

    def run(self):
        # Only start if pattern is complete
        if self.data['error']:
            print('Exited because of error check')
            self.status = 'Done'
            return False
        
        # Move to OFFSET
        self.running = True
        self.status = 'Positioning'
        for (axis, dist) in self.data['offset']:
            dist = dist*self.data['step_size']
            status = self.motor[axis].increment(dist)
            complete = self.motor[axis].wait_for_motion()
            if not complete or not status:
                print('Raster program broken off or failed during positioning!')
                self.status = 'ERR: Failed during positioning'
                for axis in ['Z', 'Y']:
                    self.motor[axis].escape()
                    status = self.motor[axis].move(self.pos[axis])
                    self.motor[axis].wait_for_motion()
                self.status = 'Done'
                return

        # Set speed
        for axis in ['Z', 'Y']:
            self.motor[axis].set_running_velocity(self.data['speed'])

        # Loop
        print('Begin rastering')
        self.status = 'Rastering'
        #print(self.pattern) # remove when checked
        size_of_pattern = len(self.pattern)
        f = open(self.logname, 'a')
        f.write('Size of pattern: {}\r\n<---->\r\n'.format(size_of_pattern))
        f.write('Counter,t_start,t1,t2,t3,t_end\r\n')
        t0 = time.time()
        while self.running and not self.motor['Z'].move_error and not self.motor['Y'].move_error:
            counter = 0
            for (axis, dist) in self.pattern:
                tstart = time.time() - t0
                counter += 1
                print('** Step {} of {} **'.format(counter, size_of_pattern))
                dist = dist*self.data['step_size']
                print(axis, dist)
                t1 = time.time() - t0
                status = self.motor[axis].increment(dist)
                t2 = time.time() - t0
                complete = self.motor[axis].wait_for_motion()
                t3 = time.time() - t0
                if not status or not complete or not self.running:
                    print('Raster program broken off during rastering!')
                    self.status = 'ERR: Rastering ended.'  
                    break
                tend = time.time() - t0
                f.write('{},{},{},{},{},{}\r\n'.format(counter, tstart, t1, t2, t3, tend))
        for axis in ['Z', 'Y']:
            f.write('Returning to center,{}\r\n'.format(time.time()-t0))
            status = self.motor[axis].move(self.pos[axis])
            complete = self.motor[axis].wait_for_motion()
            print('Should be back to origin.')
            self.motor[axis].set_running_velocity(self.vr[axis])
            # Errors encountered
            print('Error messages:')
            for i in self.motor[axis].error_msg:
                print(i)
        f.close()
        self.status = 'Done'

    def stop(self):
        """Stop raster function """
        self.running = False

import numpy as np
def timeit(cmd, num, *args, **kwargs):
    """Time a command"""

    times = np.zeros(num)
    for i in range(num):
        t0 = time.time()
        a=cmd(*args, **kwargs)
        times[i] = time.time()-t0
        #print('Lapsed time: {}'.format(np.avg))
    return times

def test_comm(cmd, t, num=20):
    t0 = time.time()
    Z._write(cmd)
    nbytes = Z.ser.inWaiting()
    for i in range(num):
        time.sleep(t)
        if Z.ser.inWaiting() > nbytes:
            nbytes = Z.ser.inWaiting()
            print(i, time.time()-t0, nbytes)
    print('Total time: {} ({} bytes)'.format(time.time()-t0, Z.ser.inWaiting()))

def fun(cmd, *args, **kwargs):
    Z._write(cmd)
    a=Z.read(*args, **kwargs)
    return a

def fun1(cmd, *args, **kwargs):
    a=Z.query(cmd, *args, **kwargs)
    return a


if __name__ == '__main__':
    print(sys.version)
    
    Z, Y = connect_Z_Y(VEXTA)
    if Z and Y:
        print('Connection succesful!')
        reply = Z.query('dpr', output='raw')
        print('*** Z_dpr ***\n')
        for i in reply:
            print(i)
        print('-'*5)
        reply = Y.query('dpr', output='raw')
        print('*** Y_dpr ***\n')
        for i in reply:
            print(i)
        print('-'*5)
    else:
        print('At least one motor connection not detected..')
