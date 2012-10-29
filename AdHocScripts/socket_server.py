import sys
import SocketServer
sys.path.append('../')
import pentax_picture as pentax

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
            print "tempNG"
        if recieved_data == "tempOld":
            print "tempOld"
        socket.sendto(data, self.client_address)

if __name__ == "__main__":
    HOST, PORT = "130.225.87.213", 9999 #Rasppi04

    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()
