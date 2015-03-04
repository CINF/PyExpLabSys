#!/bin/bash                                                                                                                              

NAME="Gasalarm307_monitor"

source /home/pi/.bashrc
export PYTHONPATH=/home/pi/PyExpLabSys

cd /home/pi/PyExpLabSys/machines/rasppi34
screen -dmS "$NAME"
screen -S "$NAME" -X screen
screen -S "$NAME" -p 0 -X stuff "python monitor.py $(printf \\r)"
