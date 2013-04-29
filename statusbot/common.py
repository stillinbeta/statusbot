from twisted.internet.protocol import Protocol
from twisted.internet.defer import Deferred

class SimpleReceiver(Protocol):
        def __init__(self, deferred, code):
            self.buf = ''
            self.deferred = deferred
            self.code = code

        def dataReceived(self, data):
            self.buf += data

        def connectionLost(self, reason):
            self.deferred.callback((self.code, self.buf))

def receive_response(response):
        d = Deferred()
        response.deliverBody(SimpleReceiver(d, response.code))
        return d


