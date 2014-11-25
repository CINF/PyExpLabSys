# pylint: disable=R0913,W0142,C0103

""" Temperature reader for microreactors """
import sys
import SocketServer
import PyExpLabSys.drivers.omega_cni as omega_CNi32
import PyExpLabSys.drivers.omegabus as omegabus
sys.path.append('../')
import pentax_picture as pentax
#import omega_CNi32 as omega_CNi32

port = 'usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0'
TC_reader = omegabus.OmegaBus('/dev/serial/by-id/' + port)

#port = 'usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0'
#omega = omega_CNi32.ISeries('/dev/serial/by-id/' + port, 9600)

#print(omega.read_temperature())
#print '----'

#This specific raspberry pi handles temperature reading
#And takes images with the pentax camera
class MyUDPHandler(SocketServer.BaseRequestHandler):

    #def __init__(self):
    #    SocketServer.BaseRequestHandler.__init__()
    #    self.key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,"PyLabView")

    def handle(self):
        recieved_data = self.request[0].strip()
        data = "test"
        socket = self.request[1]
        print recieved_data
        if recieved_data == "picture":
            pentax.AcquireImage('/usr/share/mini-httpd/html/tmp.jpg')
            data = "http://rasppi04/tmp.jpg"
        if recieved_data == "tempNG":
            data = str(omega.read_temperature())
            print data
        if recieved_data == "tempOld":
            data = str(TC_reader.ReadValue(2))
        if recieved_data == "tempRoom":
            data = str(TC_reader.ReadValue(3))
        socket.sendto(data, self.client_address)

if __name__ == "__main__":
    HOST, PORT = "10.54.7.12", 9999 #Rasppi12
    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
