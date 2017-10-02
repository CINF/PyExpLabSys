#!/bin/bash

# Padd 0 to at least 2 digits
for i in $(seq -f "%02g" 72 110)
do
    echo $i
    # Use fping for shorter than 1 sec timeout
    if fping -t 200 -c 1 rasppi$i &> /dev/null
    then
        #echo rasppi$i
        ret=`sshpass -p cinf123 ssh rasppi$i 'grep machin_dir /home/pi/.bashrc'`

        if [ ${#ret} -gt 0 ];then
            echo rasppi$i
            echo $ret
            #sshpass -p cinf123 ssh rasppi$i 'sed -i '\''s/machin_dir/machine_dir/g'\'' ~/.bashrc'
        fi
    fi
done

