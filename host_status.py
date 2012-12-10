import os#Remember to remove this
import subprocess

class HostChecker():
    
    def HostStatus(self,host):
        up = True
        
        try:
            subprocess.check_output(["ping", "-c1", "-W1", host])
        except subprocess.CalledProcessError, e:
            up = False
        return(up)

    def uptime(self,host,username='pi',password='cinf123'):
        a = subprocess.check_output(["sshpass", "-p",password, "ssh", username + "@" + host, 'uptime'])
        parts = a.split()
        uptime_string = 'Uptime, ' + parts[2] + ' ' + parts[3] + " " + parts[4][:-1] + " hours. Load: " + parts[9]
        return(uptime_string)
        
    def CheckAllHosts(self,file=None):
        status_array = []

        if file==None:
            hosts = []
            hosts.append(['agilent','Raspberry Pi','Sputterchamber'])
            hosts.append(['rasppi01','Raspberry Pi','TOF Pressure'])
            hosts.append(['rasppi02','Raspberry Pi','Mailserver'])
            hosts.append(['rasppi04','Raspberry Pi','Microreactors TC-readout'])
            hosts.append(['rasppi05','Raspberry Pi','Microreactors, temperature control'])
            hosts.append(['rasppi06','Raspberry Pi','Webcams'])
            hosts.append(['rasppi07','Raspberry Pi','NH3 Temperature and IR-signal'])
            hosts.append(['rasppi08','Raspberry Pi','Old CS, TC and pressure readout '])
            hosts.append(['microreactor','Windwos','Main PC, Microreactor'])
            hosts.append(['130.225.87.226','Windwos','Main PC, Microreactor NG'])
            hosts.append(['sputterchamber','Windwos','Sputterchamber'])
            hosts.append(['robertj','Fedora','Robert, office'])
            hosts.append(['thomas-cinf','Fedora','Thomas, office'])
        else:
            pass
            
        for host in hosts:
            up = self.HostStatus(host[0])
            if up and (host[1] == 'Raspberry Pi'):
                uptime_string = self.uptime(host[0])

        status_array.append([host[0],uptime_string])


if __name__ == "__main__":
    checker = HostChecker()

    checker.CheckAllHosts()

    hosts = []
    hosts.append(['agilent','Raspberry Pi','Sputterchamber'])
    hosts.append(['rasppi01','Raspberry Pi','TOF Pressure'])
    hosts.append(['rasppi02','Raspberry Pi','Mailserver'])
    hosts.append(['rasppi04','Raspberry Pi','Microreactors TC-readout'])
    hosts.append(['rasppi05','Raspberry Pi','Microreactors, temperature control'])
    hosts.append(['rasppi06','Raspberry Pi','Webcams'])
    hosts.append(['rasppi07','Raspberry Pi','NH3 Temperature and IR-signal'])
    hosts.append(['rasppi08','Raspberry Pi','Old CS, TC and pressure readout '])
    hosts.append(['microreactor','Windwos','Main PC, Microreactor'])
    hosts.append(['130.225.87.226','Windwos','Main PC, Microreactor NG'])
    hosts.append(['sputterchamber','Windwos','Sputterchamber'])
    hosts.append(['robertj','Fedora','Robert, office'])
    hosts.append(['thomas-cinf','Fedora','Thomas, office'])

    status_string = ""
    for host in hosts:
        status_string += host[0] + ": "
        up = checker.HostStatus(host[0])
        if up:
            status_string += "Host is up. "
            if host[1] == 'Raspberry Pi':
                status_string += checker.uptime(host[0])
        else:
            status_string += "Host is down"
        status_string += "\n"
    
    print status_string


    
