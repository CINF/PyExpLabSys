#!/bin/bash                                                                                                                              

NAME="Gasalarm312_monitor"

source /home/pi/.bashrc
export PYTHONPATH=/home/pi/PyExpLabSys

cd /home/pi/PyExpLabSys/machines/rasppi15
screen -dmS "$NAME"
screen -S "$NAME" -X screen
screen -S "$NAME" -p 0 -X stuff "python monitor.py $(printf \\r)"
