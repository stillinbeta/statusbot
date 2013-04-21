from datetime import datetime, timedelta
import getpass

import oauth2 as oauth
from twisted.application import service
from twisted.internet import reactor, task
from twisted.words.protocols.jabber.jid import JID
from wokkel.client import XMPPClient
from wokkel.xmppim import PresenceProtocol

ACCESS_KEY="1332175644-5FcBe4THbpMyF0qYendykbdggnwMasMc1XhdGvL"
ACCESS_SECRET="QiUHyn8ldmP6cu2BFOAb3V7zApobVmeDwEwrdRgI8"
ACCESS_TOKEN = oauth.Token(ACCESS_KEY, ACCESS_SECRET)

CONSUMER_KEY = '1QtQ0EMDXvymwNXiFfUg'
CONSUMER_SECRET = '4fj4RtwIjlIantT1m6VWrrS9QYW5RTtKK4Sjgd6Kw'
CONSUMER = oauth.Consumer(CONSUMER_KEY, CONSUMER_SECRET)

class PresenceFetcher(PresenceProtocol):
    RECIEVE_FOR_SECS = 2
    def __init__(self, account, interval=10):
        super(PresenceFetcher, self).__init__()
        self.account = JID(account)
        if interval - self.RECIEVE_FOR_SECS <= 0:
            raise ValueError("Interval must be greater than {}".format(
                              self.RECIEVE_FOR_SECS))

        self.interval = interval - self.RECIEVE_FOR_SECS

        self.finish_collecting = None
        self.send_results = None
        self.statuses = set()

    def sendResults(self):
        if self.statuses:
            print(self.statuses.pop())
            self.statuses = set()
        self.send_results = None
        self.finish_collecting = None
        reactor.callLater(self.interval, self.doProbe)

    def availableReceived(self, presence):
        self.statuses |= { s for s in presence.statuses.values() if s}

        if self.finish_collecting is None:
            self.finish_collecting = (
                datetime.now() + timedelta(seconds=self.RECIEVE_FOR_SECS))
        if self.send_results is not None:
            self.send_results.cancel()

        call_at = self.finish_collecting - datetime.now()
        self.send_results = reactor.callLater(call_at.seconds,
                                              self.sendResults)

    def doProbe(self):
        self.probe(self.account)

    def connectionInitialized(self):
        super(PresenceFetcher, self).connectionInitialized()
        d = self.doProbe()
        print("Initialised")

application = service.Application("statusbot")

client = XMPPClient(JID('thejapanesegeek@gmail.com/roster'), getpass.getpass())
presence = PresenceFetcher('ellie@stillinbeta.com')
presence.setHandlerParent(client)
client.setServiceParent(application)



