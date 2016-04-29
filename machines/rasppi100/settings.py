#pylint: disable-all
try:
    name = chr(0x03BC) # Python 3
except ValueError:
    name = unichr(0x03BC) # Python 2
port = '/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A602SOEK-if00-port0'
table_prefix = 'mr_chamber'

user = 'microreactor'
passwd = 'microreactor'
table = 'dateplots_microreactor'
