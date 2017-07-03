#!/bin/bash

export PYTHONPATH=$HOME/PyExpLabSys

/usr/bin/python2 /home/cinf/PyExpLabSys/machines/proactive_H2O2/voltage_current_program.py B 2 steps_B2.yaml

read -p "Press [Enter] to exit"
