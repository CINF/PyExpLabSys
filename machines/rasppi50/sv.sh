NAME="autostart"

cd /home/pi/PyExpLabSys/machines/rasppi50
screen -dmS "$NAME"
screen -S "$NAME" -X screen
screen -S "$NAME" -p 0 -X stuff "python socket_server.py $(printf \\r)"

