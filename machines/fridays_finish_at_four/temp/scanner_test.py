import sys

fp = open('/dev/hidraw0', 'rb')

while True:
   buffer = fp.read(8)
   #print buffer
   for c in buffer:
      if ord(c) > 0:
         print repr(chr(ord(c) + 19))
         #print c
   #print "\n"
