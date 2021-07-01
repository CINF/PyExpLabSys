#!/usr/bin/python

import os
import time

def GetUsbList():
  return os.popen("lsusb").read().strip().split("\n")

def GetDevList():
  return os.listdir("/dev")

def Changed(old,now):
  add = []
  rem = []
  for this in now:
    if not this in old:
      add.append(this)
  for this in old:
    if not this in now:
      rem.append(this)
  return add, rem

try:
  print("Monitoring for USB changes and changes in /dev directory")
  usbOld = GetUsbList()
  devOld = GetDevList()
  while True:
    time.sleep(1)
    usbNow = GetUsbList()
    devNow = GetDevList()
    usbAdd, usbRem = Changed(usbOld,usbNow)
    devAdd, devRem = Changed(devOld,devNow)
    if len(usbAdd) + len(usbRem) + len(devAdd) + len(devRem) > 0:
      print("-------------------")
      t = time.strftime("%Y-%m-%d %H:%M:%S - ")
      for this in usbAdd : print(t + "Added   : " + this)
      for this in usbRem : print(t + "Removed : " + this)
      for this in devAdd : print(t + "Added   : /dev/" + this)
      for this in devRem : print(t + "Removed : /dev/" + this)
      usbOld = usbNow
      devOld = devNow
except KeyboardInterrupt:
  print("")
