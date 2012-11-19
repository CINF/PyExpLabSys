command_string = []
command_string.append(ord('#'))
command_string.append(ord('@'))
crc = int('3fff',16)
mask = int('2001',16)

for command in command_string:
    crc = command ^ crc
    for i in range(0,8):
        old_crc = crc
        crc  = crc >> 1
        if old_crc % 2 == 1:
            crc = crc ^ mask

crc1 =  crc % 64
crc2 = crc >> 7
print chr(crc1 + 34)
print chr(crc2 + 34)
