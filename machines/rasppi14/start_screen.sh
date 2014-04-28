NAME="autostart"

cd /home/pi/PyExpLabSys/rasppi14
screen -dmS "$NAME"
screen -S "$NAME" -X screen
screen -S "$NAME" -p 0 -X stuff "python socket_server.py $(printf \\r)"
screen -S "$NAME" -p 1 -X stuff "python data_logger.py $(printf \\r)"