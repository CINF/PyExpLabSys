import os#Remember to remove this
import subprocess

hosts = []
hosts.append(['rasppi06','Raspberry Pi','Webcams'])
hosts.append(['rasppi07','Raspberry Pi','NH3 Temperature and IR-signal'])

for host in hosts:
    status_string = host[0] + ": "

    try:
        subprocess.check_output(["ping", "-c1", "-W1", host[0]])
    except:
        status_string += "Host is down"
        print status_string
    #ret = os.system("ping -W1 -c 1 " + host[0] + ">/dev/null")
    #if ret > 0:
    #    status_string += "Host is down"
    #else:
    #    status_string += "Host is running"
        
        #sshpass -p cinf123 ssh pi@rasppi01 uptime