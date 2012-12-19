import subprocess
import urllib2

class HostChecker():
    
    def HostStatus(self,host):
        up = True
        
        try:
            subprocess.check_output(["ping", "-c1", "-W1", host])
        except subprocess.CalledProcessError, e:
            up = False
        return(up)

    def uptime(self,host,method,username='pi',password='cinf123'):
        uptime_string = ""
        if method == 'ssh':
            uptime_string = subprocess.check_output(["sshpass", "-p",password, "ssh",'-o LogLevel=quiet','-oUserKnownHostsFile=/dev/null', '-oStrictHostKeyChecking=no', username + "@" + host, 'uptime'])
        if method== 'http':
            f = urllib2.urlopen('http://' + host + '/uptime.php')
            uptime_string = f.read()
            f.close()

        if uptime_string!="":
            parts = uptime_string.split()
            return_string = parts[2] + ' ' + parts[3] + " " + parts[4][:-1] + " hours. Load: " + parts[9]
        else:
            return_string = ""
        return(return_string)
        
    def CheckAllHosts(self,file=None):
        status_array = []

        if file==None:
            hosts = []
            hosts.append(['agilent','Raspberry Pi','ssh','Sputterchamber'])
            hosts.append(['rasppi01','Raspberry Pi','ssh','TOF Pressure'])
            hosts.append(['rasppi02','Raspberry Pi','ssh','Mailserver'])
            hosts.append(['rasppi04','Raspberry Pi','ssh','Microreactors TC-readout'])
            hosts.append(['rasppi05','Raspberry Pi','ssh','Microreactors, temperature control'])
            hosts.append(['rasppi06','Raspberry Pi','ssh','Webcams'])
            hosts.append(['rasppi07','Raspberry Pi','ssh','NH3 Temperature and IR-signal'])
            hosts.append(['rasppi08','Raspberry Pi','ssh','Old CS, TC and pressure readout '])
            hosts.append(['microreactor','Windows','None','Main PC, Microreactor'])
            hosts.append(['130.225.87.226','Windows','None','Main PC, Microreactor NG'])
            hosts.append(['tofms','Windows','None','TOF-MS'])
            hosts.append(['sputterchamber','Windows','None','Sputterchamber'])
            hosts.append(['hot-e2','Windows','None','NH3 setup, main pc'])
            hosts.append(['gibbs','Fedora','None','Robert, test server'])
            hosts.append(['robertj','Fedora','http','Robert, office'])
            hosts.append(['thomas-cinf','Fedora','None','Thomas, office'])
        else:
            pass
            
        for host in hosts:
            up = self.HostStatus(host[0])
            if up:
                uptime_string = self.uptime(host[0],host[2])
            else:
                uptime_string = ""

            status_array.append([host[0],up,uptime_string,host[3],host[1]])
        return(status_array)

    def show_status(self,file=None):
        if file==None:
            host_status = self.CheckAllHosts()
        else:
            host_status = self.CheckAllHosts(file)
            
        status_string = ""
        for host in host_status:
            status_string += host[0] + ";"
            if host[1]:
                status_string += "1;"
                status_string += host[2] + ";"
            else:
                status_string += "0;;"
            status_string += host[3] + ";"
            status_string += host[4]
            status_string += "\n"
        return(status_string)


if __name__ == "__main__":

    checker = HostChecker()

    #host_status = checker.CheckAllHosts()

    #status_string = ""
    #for host in host_status:
    #    status_string += host[0] + ": "
    #    if host[1]:
    #        status_string += "Host is up. "
    #        status_string += host[2]
    #    else:
    #        status_string += "Host is down"
    #    status_string += "\n"
    #print status_string

    print checker.show_status()
