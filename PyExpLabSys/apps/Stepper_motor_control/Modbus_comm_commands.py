import minimalmodbus
from PyExpLabSys.common.supported_versions import python3_only

python3_only(__file__)
import time


class Motor(object):
    def __init__(self, port, slave_adress=1):
        self.instrument = minimalmodbus.Instrument(
            port, slave_adress, mode=minimalmodbus.MODE_RTU
        )
        self.instrument.serial.baudrate = 9600
        self.instrument.serial.bytesize = 8
        self.instrument.serial.parity = minimalmodbus.serial.PARITY_EVEN
        self.instrument.serial.stopbits = 1
        self.instrument.serial.timeout = 1  # seconds

    """ Maintenance """

    def get_status(self):
        try:
            response = self.instrument.read_long(126, signed=True)
            status = int('{0:b}'.format(response)[-6])
        except IndexError:
            status = 0
        return status

    def get_home_end(self):
        try:
            response = self.instrument.read_long(126, signed=True)
            status = int('{0:b}'.format(response)[-5])
        except IndexError:
            status = 0
        return status

    def get_move(self):
        try:
            response = self.instrument.read_long(126, signed=True)
            status = int('{0:b}'.format(response)[-14])
        except IndexError:
            status = 0
        return status

    def get_alarm(self):
        response = self.instrument.read_long(128, signed=True)
        response = hex(response)[2:]
        return response

    def reset_alarm(self):
        self.instrument.write_long(384, 1, signed=True)
        self.instrument.write_long(384, 0, signed=True)

    def get_alarm_record(self):
        alarm_record = []
        for i in range(10):
            response = self.instrument.read_long(130 + 2 * i, signed=True)
            alarm_record.append(hex(response)[2:])
        return alarm_record

    def clear_alarm_record(self):
        self.instrument.write_long(388, 1, signed=True)
        self.instrument.write_long(388, 0, signed=True)

    def get_alarm_status(self):
        try:
            response = self.instrument.read_long(126, signed=True)
            status = int('{0:b}'.format(response)[-8])
        except IndexError:
            status = 0
        return status

    def clear_ETO(self):
        " Clear the ETO (External Torque Off) mode "
        self.instrument.write_long(416, 1, signed=True)
        self.instrument.write_long(416, 0, signed=True)

    def save_RAM_to_non_volatile(self):
        " Writes the parameters saved in the RAM to the non-volatile memory, which can be rewritten approx. 100,000 times "
        self.instrument.write_long(402, 1, signed=True)
        time.sleep(0.1)
        self.instrument.write_long(402, 0, signed=True)

    def load_non_volatile_to_RAM(self):
        " Read the parameters saved in the non-volatile memory to the RAM. NB! All operation data and parameters saved in the RAM are overwritten "
        self.instrument.write_long(400, 1, signed=True)
        self.instrument.write_long(400, 0, signed=True)

    def load_RAM_to_direct(self):
        " Read and write the operation data number to be used in direct data operation "
        operation_number = self.instrument.read_long(88, signed=True)
        self.instrument.write_long(88, operation_number, signed=True)

    """ Commands required for direct data operation. Set values are stored in RAM """

    """ Read """

    def get_operation_data_number(self):
        response = self.instrument.read_long(88, signed=True)
        return response

    def get_operation_trigger(self):
        response = self.instrument.read_long(102, signed=True)
        return response

    def get_operation_type(self):
        response = self.instrument.read_long(90, signed=True)
        return response

    def get_operating_speed(self):
        response = self.instrument.read_long(94, signed=True)
        return response

    def get_starting_changing_rate(self):
        response = self.instrument.read_long(96, signed=True) / 1000
        return response

    def get_stopping_deceleration(self):
        response = self.instrument.read_long(98, signed=True) / 1000
        return response

    def get_operating_current(self):
        response = self.instrument.read_long(100, signed=True) / 10
        return response

    def get_position(self):
        response = self.instrument.read_long(92, signed=True) / 100
        return response

    def get_command_position(self):
        response = self.instrument.read_long(198, signed=True) / 100
        return response

    def get_group_id(self):
        response = self.instrument.read_long(48, signed=True)
        return response

    """ Write """

    def set_operation_data_number(self, setting):
        self.instrument.write_long(88, setting, signed=True)

    def set_operation_trigger(self, setting):
        self.instrument.write_long(102, setting, signed=True)

    def set_operation_type(self, setting):
        self.instrument.write_long(90, setting, signed=True)

    def set_position(self, setting):
        self.instrument.write_long(92, int(setting * 100), signed=True)

    def set_operating_speed(self, setting):
        self.instrument.write_long(94, setting, signed=True)

    def set_starting_changing_rate(self, setting):
        self.instrument.write_long(96, setting * 1000, signed=True)

    def set_stopping_deceleration(self, setting):
        self.instrument.write_long(98, setting * 1000, signed=True)

    def set_operating_current(self, setting):
        self.instrument.write_long(100, setting * 10, signed=True)

    def set_group_id(self, parent_slave):
        self.instrument.write_long(48, parent_slave, signed=True)

    def home(self):
        # Binary code to write 0000000000010000 = 16
        self.instrument.write_long(124, 16, signed=True)
        self.instrument.write_long(124, 0, signed=True)

    def stop(self):
        self.instrument.write_long(124, 32, signed=True)
        self.instrument.write_long(124, 0, signed=True)

    """ Commands required for initial data operation """
    """ Input is made by operation data number. Below are functions to read from and write to the registers corresponding to operation data No. 0 to 63. Settable items are: Type, position, operating speed, starting/changing rate, stop, and operating current """

    """ Read """

    def get_initial_group_id(self):
        response = self.instrument.read_long(5012, signed=True)
        return response

    def get_initial_position(self, operation_number):
        response = (
            self.instrument.read_long(1024 + operation_number * 2, signed=True) / 100
        )
        return response

    def get_initial_operating_speed(self):
        response = self.instrument.read_long(1152, signed=True)
        return response

    def get_initial_starting_speed(self):
        response = self.instrument.read_long(644, signed=True)
        return response

    def get_initial_starting_changing_rate(self):
        response = self.instrument.read_long(1536, signed=True) / 1000
        return response

    def get_initial_stopping_deceleration(self):
        response = self.instrument.read_long(1664, signed=True) / 1000
        return response

    def get_initial_operating_current(self):
        response = self.instrument.read_long(1792, signed=True) / 10
        return response

    def get_initial_operation_type(self, operation_number):
        response = self.instrument.read_long(1280 + operation_number * 2, signed=True)
        return response

    def get_initial_positive_software_limit(self):
        response = self.instrument.read_long(904, signed=True) / 100
        return response

    def get_initial_negative_software_limit(self):
        response = self.instrument.read_long(906, signed=True) / 100
        return response

    def get_initial_electronic_gear_A(self):
        response = self.instrument.read_long(896, signed=True)
        return response

    def get_initial_electronic_gear_B(self):
        response = self.instrument.read_long(898, signed=True)
        return response

    def get_initial_zhome_operating_speed(self):
        response = self.instrument.read_long(688, signed=True)
        return response

    def get_initial_zhome_starting_speed(self):
        response = self.instrument.read_long(692, signed=True)
        return response

    def get_initial_zhome_acceleration_deceleration(self):
        response = self.instrument.read_long(690, signed=True) / 1000
        return response

    def get_Home_location(self):
        operation_number = 1
        response = (
            self.instrument.read_long(1024 + operation_number * 2, signed=True) / 100
        )
        return response

    def get_ISS_location(self):
        operation_number = 2
        response = (
            self.instrument.read_long(1024 + operation_number * 2, signed=True) / 100
        )
        return response

    def get_Mg_XPS_location(self):
        operation_number = 3
        response = (
            self.instrument.read_long(1024 + operation_number * 2, signed=True) / 100
        )
        return response

    def get_Al_XPS_location(self):
        operation_number = 4
        response = (
            self.instrument.read_long(1024 + operation_number * 2, signed=True) / 100
        )
        return response

    def get_SIG_location(self):
        operation_number = 5
        response = (
            self.instrument.read_long(1024 + operation_number * 2, signed=True) / 100
        )
        return response

    def get_HPC_location(self):
        operation_number = 6
        response = (
            self.instrument.read_long(1024 + operation_number * 2, signed=True) / 100
        )
        return response

    def get_Baking_location(self):
        operation_number = 7
        response = (
            self.instrument.read_long(1024 + operation_number * 2, signed=True) / 100
        )
        return response

    """ Write """

    def set_initial_position(self, operation_number, setting):
        """ Setting range: -2,147,438,648 to 2,147,438,648 steps """
        self.instrument.write_long(
            1024 + operation_number * 2, setting * 100, signed=True
        )

    def set_initial_operating_speed(self, setting):
        """ Setting range: -4,000,000 to 4,000,000 Hz  """
        self.instrument.write_long(1152, int(setting), signed=True)

    def set_initial_starting_speed(self, setting):
        """ Setting range: 0 to 4,000,000 Hz  """
        self.instrument.write_long(644, int(setting), signed=True)

    def set_initial_starting_changing_rate(self, setting):
        """ Setting range: 1 to 1,000,000,000 (unit is kHz/s, s or ms/kHz) """
        self.instrument.write_long(1536, int(setting * 1000), signed=True)

    def set_initial_stopping_deceleration(self, setting):
        """ Setting range: 1 to 1,000,000,000 (unit is kHz/s, s or ms/kHz) """
        self.instrument.write_long(1664, int(setting * 1000), signed=True)

    def set_initial_operating_current(self, setting):
        """ Setting range: 0 to 1,000 (1=0.1 %) """
        self.instrument.write_long(1792, int(setting * 10), signed=True)

    def set_initial_operation_type(self, operation_number, setting):
        self.instrument.write_long(1280 + operation_number * 2, setting, signed=True)

    def set_initial_group_id(self, parent_slave):
        """ Setting range: -1: Disable (no group transmission, initial value); 1 to 31: Group ID 1 to 31. NB! Do not use 0 """
        self.instrument.write_long(5012, int(parent_slave), signed=True)

    def set_initial_positive_software_limit(self, setting):
        self.instrument.write_long(904, int(setting * 100), signed=True)

    def set_initial_negative_software_limit(self, setting):
        self.instrument.write_long(906, int(setting * 100), signed=True)

    def set_initial_electronic_gear_A(self, setting):
        self.instrument.write_long(896, int(setting), signed=True)

    def set_initial_electronic_gear_B(self, setting):
        self.instrument.write_long(898, int(setting), signed=True)

    def set_initial_zhome_operating_speed(self, setting):
        self.instrument.write_long(688, int(setting), signed=True)

    def set_initial_zhome_starting_speed(self, setting):
        self.instrument.write_long(692, int(setting), signed=True)

    def set_initial_zhome_acceleration_deceleration(self, setting):
        self.instrument.write_long(690, int(setting * 1000), signed=True)

    def set_ISS_location(self, setting):
        operation_number = 2
        self.instrument.write_long(
            1024 + operation_number * 2, int(setting * 100), signed=True
        )

    def set_Mg_XPS_location(self, setting):
        operation_number = 3
        self.instrument.write_long(
            1024 + operation_number * 2, int(setting * 100), signed=True
        )

    def set_Al_XPS_location(self, setting):
        operation_number = 4
        self.instrument.write_long(
            1024 + operation_number * 2, int(setting * 100), signed=True
        )

    def set_SIG_location(self, setting):
        operation_number = 5
        self.instrument.write_long(
            1024 + operation_number * 2, int(setting * 100), signed=True
        )

    def set_HPC_location(self, setting):
        operation_number = 6
        self.instrument.write_long(
            1024 + operation_number * 2, int(setting * 100), signed=True
        )

    def set_Baking_location(self, setting):
        operation_number = 7
        self.instrument.write_long(
            1024 + operation_number * 2, int(setting * 100), signed=True
        )
