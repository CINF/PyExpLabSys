#!/bin/bash

export PYTHONPATH=$HOME/PyExpLabSys

/usr/bin/python2 /home/cinf/PyExpLabSys/machines/proactive_H2O2/voltage_current_program.py C 1 steps_C1.yaml

read -p "Press [Enter] to exit"
