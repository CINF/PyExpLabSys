
f.serial.baudrate = 9600
f.serial.parity = serial.PARITY_EVEN
f.serial.timeout = 0.25
print f.serial

for i in range(0, 100):
    print f.read_register( 4096, 1)
