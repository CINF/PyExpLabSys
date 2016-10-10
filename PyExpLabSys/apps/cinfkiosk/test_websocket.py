
#import sys
import json
import threading


#from twisted.python import log
from twisted.internet import reactor
#log.startLogging(sys.stdout)

from autobahn.twisted.websocket import (WebSocketClientProtocol, \
    WebSocketClientFactory, connectWS)



class MyClientProtocol(WebSocketClientProtocol):

    def onConnect(self, response):
        print("### Server connected: {0}".format(response.peer))

    def onOpen(self):
        subscribe = {
            u'action': u'subscribe',
            u'subscriptions': [u'rasppi71:thetaprobe_main_chamber_pressure',
                               u'rasppi25:thetaprobe_pressure_loadlock',
                               u'rasppi71:thetaprobe_load_lock_roughing_pressure',
                               u'rasppi71:thetaprobe_main_chamber_temperature']
        }
        self.sendMessage(json.dumps(subscribe).encode('ascii'))
        print("### WebSocket connection open.")

    def onMessage(self, payload, isBinary):
        if isBinary:
            print("### Binary message received: {0} bytes".format(len(payload)))
        else:
            print("### Text message received: {0}".format(payload.decode('utf8')))

    def onClose(self, wasClean, code, reason):
        print("### WebSocket connection closed: {0}".format(reason))


if __name__ == '__main__':

    factory = WebSocketClientFactory(url="wss://cinf-wsserver.fysik.dtu.dk:9002")
    factory.protocol = MyClientProtocol

    from twisted.internet import reactor, ssl
    if factory.isSecure:
        contextFactory = ssl.ClientContextFactory()
    else:
        contextFactory = None

    connectWS(factory, contextFactory)

    #reactor.connectTCP("https://cinf-wsserver.fysik.dtu.dk", 9002, factory)

    from threading import Thread

    Thread(target=reactor.run, args=(False,)).start()

    try:
        time.sleep(10000000)
    except KeyboardInterrupt:
        reactor.stop()

    #reactor.run()
    print("HH")


    
