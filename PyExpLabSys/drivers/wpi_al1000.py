
"""This module implements a driver for the AL1000 syringe pump from
World Precision Instruments

"""


import serial
import time
import crc16


class AL1000(object):
    """Driver for the AL1000 syringe pump"""
    
    def __init__(self, port="/dev/ttyUSB0", baudrate=19200):
        self.serial = serial.Serial(
            port=port, baudrate=baudrate, timeout=1,
            parity=serial.PARITY_NONE,
            bytesize=serial.EIGHTBITS,
            stopbits=serial.STOPBITS_ONE,
            
        )
        self.safe_mode = False

    def _send_command(self, command):
        if self.safe_mode:
            encoded_command = command.encode('ascii')
            length = len(encoded_command) + 4
            check_sum = crc16.crc16xmodem(encoded_command).to_bytes(2, byteorder='big')
            to_send = bytes([2, length]) + encoded_command + check_sum + b'\x03'
            add = '{:0>2}'.format(n).encode('ascii')
            to_send_add = add + to_send
            self.serial.write(to_send)
            time.sleep(0.5)
            waiting = self.serial.inWaiting()
            reply = self.serial.read(waiting)

            # FIXME implement crc16 checksum check
            
            return reply.decode('ascii')
        else:
            formatted_command = command + "\r"
            self.serial.write(formatted_command.encode("ascii"))
            time.sleep(0.5)
            waiting = self.serial.inWaiting()
            reply = self.serial.read(waiting)
            reply_unicode = reply.decode("ascii")
            return reply_unicode[4:-1]

    def get_firmware(self):
        """Retrieves the firmware version
        
        Returns:
            str: The firmware version
        """
        return self._send_command("VER")

    def get_rate(self):
        """
        Retrieves the pump rate
        
        Returns:
            The pumping rate 
            
        """
        # FIXME convert to float
        return self._send_command("RAT")

    def set_rate(self, num, unit = False):
        """Sets the pump rate.
        
        Args:
            num (float): The flow rate (0 mL/min - 34.38 mL/min)
            unit (str): For valid values see below.
        

        Valid units are:
        UM=microL/min
        MM=milliL/min 
        UH=microL/hr 
        MH=milliL/hour
        
        Returns:
            Notihing. Printing the function yields space for success or error message
            
        """
        if unit == False:
            self._send_command("FUNRAT")
            return "rate: " + self._send_command("RAT" + str(num))
            
        if unit != False:
            
            self._send_command("FUNRAT")
            return "rate: " + self._send_command("RAT" + str(num) + unit )

    def set_vol(self,num):
        """Sets the pumped volume to the pump. The pump will pump until the given volume has been dispensed.
        
        Args:
            num (float): The volume to de dispensed (no limits)

        Returns:
            Notihing. Printing the function yields space for success or error message
            
        """
        return self._send_command("VOL" + str(num))

    def get_vol_disp(self):
        """Retrieves the dispensed volume since last reset.

        Returns:
            The dispensed volume
        """
        return self._send_command("DIS")
    
    def clear_vol_disp(self, direction = "both"):
        """Clear pumped volume for one or more dircetions. 
        
        Args:
            direction (string): The pumping direction. Valid directions are: INF=inflation, WDR=withdrawn, both=both directions. Default is both
        
        Returns:
            Notihing. Printing the function yields space for success or error message

        """
        if direction == "INF":
            return self._send_command("CLDINF")
        if direction == "WDR":
            return self._send_command("CLDWDR")
        if direction == "both":
            return self._send_command("CLDINF")
            return self._send_command("CLDWDR")
                        
    def set_fun(self, phase):
        """Sets the program function
        
        Returns:
            Notihing. Printing the function yields space for success or error message

        """
        return self._send_command("FUN" + phase)

    def set_safe_mode(self,num):
        """Enables or disables safe mode.
        
        Args:
            If num=0 --> Safe mode disables
                If num>0 --> Safe mode enables with the requirement that valid communication must be received every num seconds
        
        Returns:
            Notihing. Printing the function yields space for success or error message        

        """
        return self._send_command("SAF" + str(num))

    def start_program(self):
        return self._send_command("RUN")

    def stop_program(self):
        return self._send_command("STP")

    def get_direction(self):
        """Retrieves the curret pumping direction"""
        return self._send_command("DIR")

    def set_direction(self, direction):
        """Sets the pumping direction
        
        Args:
            directoin=INF --> Pumping dirction set to infuse
                directoin=WDR --> Pumping dirction set to Withdraw
                    directoin=REV --> Pumping dirction set to the reverse current pumping direction
        
        Returns:
            Notihing. Printing the function yields space for success or error message        

        """
        if direction == "INF":
            return self._send_command("DIRINF")
        if direction == "WDR":
            return self._send_command("DIRWDR")
        if direction == "REV":
            return self._send_command("DIRREV")

    def retract_pump(self):
        """Fully retracts the pump. REMEMBER TO STOP MANUALLY!
        
        Returns:
            Notihing. Printing the function yields space for success or error message        

        """
        self.set_direction("WDR")
        self.set_vol(9999)
        self.set_rate(34.38,"MM")
        self.start_program()

max_rate = 34.38

def main():
    pump = AL1000()
    print(repr(pump.get_firmware()))
    #print(repr(pump._send_command("\x02\x08SAF0\x55\x43\x03")))

if __name__ == "__main__" :
    main()
