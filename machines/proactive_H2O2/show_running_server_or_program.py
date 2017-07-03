# -*- coding: utf-8 -*-
"""
Created on Tue Sep 27 09:15:05 2016

@author: CINF
"""

#from subprocess import check_output
import subprocess

def count_processes(process_search_string, ignore=('cmd.exe', 'spyder')):
    """Return the number of processes that contain process_search_string"""
    # Hack found online to prevent Windows from opening a terminal
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    # Ask Windows about its processes
    processes_bytes = subprocess.check_output(
        'wmic process get processid,commandline',
        startupinfo=startupinfo,
    )
    # Decode split into lines, lowercase and strip
    processes = processes_bytes.decode('utf-8', errors='ignore').split('\r\r\n')
    processes = [process.strip().lower() for process in processes]

    # Find the processes that contain the search word and not any of the igore terms
    processes_filtered = []
    for process in processes:
        if not process_search_string in process:
            continue

        # If any of the ignore terms are found, break and thereby never reach the append
        # in the else clause
        for ignore_term in ignore:
            if ignore_term in process:
                break
        else:
            processes_filtered.append(process)
    return len(processes_filtered)



print('Voltage current program:', count_processes('voltage_current_program'))
print('power supply server:', count_processes('power_supply_server'))
input("Press ay key to exit")