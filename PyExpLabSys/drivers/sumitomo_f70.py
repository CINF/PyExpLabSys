import time
import serial

# # Read firmware version
# # comm = 'ID1D629' + '\r'

class SumitomoF70(object):
    def __init__(self, port='/dev/ttyUSB0'):
        # Default comm parameters are correct, we could choose to set them though
        self.serial = serial.Serial(port)

    @staticmethod
    def _crc(command):
        # Adapted from https://github.com/Kalebu/crc16-modbus-in-Python
        xor_value = 0xA001
        crc = 0xFFFF
        for byte in command:
            crc = crc ^ ord(byte)
            for _ in range(8):
                if (crc & 1):  # LSB is 1
                    crc = crc >> 1
                    crc = crc ^ xor_value
                else:
                    crc = crc >> 1

        return_val = hex(crc)[2:].upper()
        return return_val
        
    def _comm(self, command):
        comm = command + self._crc(command) + '\r'
        comm = comm.encode('ascii')       
        self.serial.write(comm)
        reply = self.serial.read_until(b'\r')

        expected_crc = self._crc(reply[:-5].decode())
        actual_crc = reply[-5:-1].decode()
        if expected_crc == actual_crc:
            pre_cut = len(command) + 1  # Original command + comma
            post_cut = -6  #  comma, 4 crc digits, CR
            return_val = reply[pre_cut:post_cut].decode()
        else:
            print('CRC error')
            return_val = None
        
        return return_val

    def read_temperature(self):
        command = '$TEA'
        reply_raw = self._comm(command)
        temperatures_raw = reply_raw.split(',')
        temperatures = {
            'discharge_temp': float(temperatures_raw[0]),
            'water_outlet_temp': float(temperatures_raw[1]),
            'water_inlet_temp': float(temperatures_raw[2]),
        }
        return temperatures

    def read_pressure(self):
        command = '$PRA'
        reply_raw = self._comm(command)
        pressure = float(reply_raw.split(',')[0])
        pressure_in_bar = pressure * 0.0689476
        return pressure_in_bar

    def read_status(self):
        command = '$STA'
        raw_reply = self._comm(command)
        print(raw_reply)
        # raw_reply = '0301'
        msb = int(raw_reply[0:2], 16)
        lsb = int(raw_reply[2:4], 16)

        print(bin(msb)[2:].zfill(8))
        print(bin(lsb)[2:].zfill(8))

        
        system_on =           bool(lsb & 0b00000001)
        motor_alam =          bool(lsb & 0b00000010)
        phase_sequence_alam = bool(lsb & 0b00000100)
        helium_temp_alam =    bool(lsb & 0b00001000)
        water_temp_alam =     bool(lsb & 0b00010000)
        water_flow_alam =     bool(lsb & 0b00100000)
        oil_level_alam =      bool(lsb & 0b01000000)
        pressure_alam =       bool(lsb & 0b10000000)

        solenoid_on =         bool(msb & 0b00000001)

        # state_lsb =           msb & 0b00000010
        # state_center =        msb & 0b00000100
        # state_msb =           msb & 0b00001000
        state = 0b111 & (msb >> 1)
        
        configureation_bit =  msb & 0b10000000

        print(state_lsb, state_center, 
        
        status = {
            'system_on': system_on,
        }
        return status
        
if __name__ == '__main__':
    F70 = SuitomoF70()
    # print('temperature')
    # print(F70.read_temperature())
    # print()
    # print('pressure')
    # for i in range(0, 10):
    #     time.sleep(0.1)
    #     print(F70.read_pressure())
    # print()
    print('status')
    print(F70.read_status())

