import sys
import SocketServer
sys.path.append('../')
import pentax_picture as pentax
import omegabus

TC_reader = omegabus.OmegaBus()

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
            data = str(TC_reader.ReadValue(1))
        if recieved_data == "tempOld":
            data = str(TC_reader.ReadValue(2))
        if recieved_data == "tempRoom":
            data = str(TC_reader.ReadValue(3))
        socket.sendto(data, self.client_address)

if __name__ == "__main__":
    HOST, PORT = "130.225.86.181", 9999 #Rasppi12

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
