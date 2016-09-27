# -*- coding: utf-8 -*-
"""
Created on Tue Sep 27 09:15:05 2016

@author: CINF
"""

from subprocess import check_output, Popen



#Popen(r'C:\Users\CINF\Anaconda3\python.exe test_server.py', shell=True)



#processes_bytes = check_output('wmic process get description,executablepath')
processes_bytes = check_output('wmic process get processid,commandline')
processes = processes_bytes.decode('utf-8', errors='ignore').split('\r\r\n')
processes = [process.strip().lower() for process in processes]


for line in processes:
    if 'cmd.exe' in line:
        continue
    if 'power_supply_server' in line:
        print('test_server running')
    if 'voltage_current_program' in line:
        print('program running')

print('Done')