import SocketServer
import _winreg as winreg

class MyUDPHandler(SocketServer.BaseRequestHandler):

    #def __init__(self):
    #    SocketServer.BaseRequestHandler.__init__()
    #    self.key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,"PyLabView")

    def string_to_registry(self,string):
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,"PyLabView")
        for element in string.split(';'):
            splitted_element = element.split('=')
            winreg.SetValueEx(key,splitted_element[0],0,winreg.REG_SZ,splitted_element[1])
            
    def registry_to_string(self,parameters):    
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,"PyLabView")
        string = ""
        for parameter in parameters:
            registry_param = winreg.QueryValueEx(key,parameter)
            string = string + parameter + '=' + registry_param[0] + ';'
        return string[:-1]
        
    def handle(self):
        recieved_data = self.request[0].strip()
        self.string_to_registry(recieved_data)
        parameters = ['sample_temperature','setpoint']
        data = self.registry_to_string(parameters)
        socket = self.request[1]
        #print recieved_data
        socket.sendto(data, self.client_address)

if __name__ == "__main__":
    HOST, PORT = "130.225.87.226", 9999 #MicroreactorNG
    
    server = SocketServer.UDPServer((HOST, PORT), MyUDPHandler)
    server.serve_forever()