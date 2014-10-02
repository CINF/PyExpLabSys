#!/bin/bash                                                                                                                              

NAME="coupled_reactor_temp"

source /home/pi/.bashrc
export PYTHONPATH=/home/pi/PyExpLabSys

cd /home/pi/PyExpLabSys/machines/rasppi41
screen -dmS "$NAME"
screen -S "$NAME" -X screen
screen -S "$NAME" -p 0 -X stuff "python temperature_logger.py $(printf \\r)"