#!/bin/bash

pages[0]=https://cinfdata.fysik.dtu.dk/hall/live.php?type=live_values_fm
#pages[1]=https://cinfdata.fysik.dtu.dk/gasmonitor307/live.php?type=live_values_pager
#pages[2]=https://cinfdata.fysik.dtu.dk/gasmonitor312/live.php?type=live_values_pager
#pages[3]=https://cinfdata.fysik.dtu.dk/chillers/live.php?type=live_values

sleep 10
killall firefox
sleep 10

for page in ${pages[*]};do
    firefox -P 'fullscreen' -new-tab $page &
    sleep 5
done


