#!/bin/bash
while :
do
    gpio write 2 0
    sleep 10
    gpio write 2 1
    sleep 590
done
