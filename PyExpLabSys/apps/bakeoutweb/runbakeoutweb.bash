#!/bin/bash



helptext="\nRun the bakeout web application

Usage:
    runbakeoutweb.bash machine [debug]
"


function help(){
    echo -e  "$helptext"
}


# Check that there are 1 or 2 arguments
if [ $# -lt 1 ] || [ $# -gt 2 ];then
    help
    exit 1
fi

export FLASK_APP=tmp.py

# Check whether debug mode is requested
if [ $# -eq 2 ] && [ $2 == "debug" ];then
    echo "Running in debug mode"
    export FLASK_DEBUG=1
    python3 -m flask run
else
    python3 -m flask run --host=0.0.0.0
fi
