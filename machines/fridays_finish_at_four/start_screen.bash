#!/bin/bash

NAME="autostart"

source /home/pi/.bashrc
export PYTHONPATH=/home/pi/PyExpLabSys

cd /home/pi/PyExpLabSys/machines/fridays_finish_at_four
screen -dmS "$NAME"
screen -S "$NAME" -X screen
#screen -S "$NAME" -p 0 -X stuff "python BarProgramme.py $(printf \\r)"
screen -S "$NAME" -p 0 -X stuff "python bar_program.py $(printf \\r)"
