#!/usr/bin/env python

from __future__ import print_function

import sys
from time import time, sleep

while True:
    print(sys.argv[1], time())
    sleep(1)
