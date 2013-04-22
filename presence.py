from __future__ import print_function

from datetime import datetime, timedelta
import getpass

import oauth2 as oauth
from twisted.application import service
from twisted.internet.defer import Deferred
from twisted.internet.task import LoopingCall
from twisted.words.protocols.jabber.jid import JID
from wokkel.client import XMPPClient
from wokkel.xmppim import PresenceProtocol

class PresenceFetcher(PresenceProtocol):
    RECIEVE_FOR_SECS = 2

    class StatusJobState(object):
        def __init__(self, deferred):
            self.deferred = deferred
            self.statuses = set()

    def __init__(self):
        super(PresenceFetcher, self).__init__()
        self.statusJobs = {}

    def sendResults(self, userhost):
        jobState = self.statusJobs.pop(userhost)
        jobState.deferred.callback(list(jobState.statuses))

    def availableReceived(self, presence):
        userhost = presence.sender.userhost()
        jobState = self.statusJobs[userhost]
        jobState.statuses |= {s for s in presence.statuses.values() if s}

    def doProbe(self, account):
        d = Deferred()

        from twisted.internet import reactor
        reactor.callLater(self.RECIEVE_FOR_SECS,
                          self.sendResults,
                          account.userhost())
        self.statusJobs[account.userhost()] = self.StatusJobState(d)
        self.probe(account)
        return d

class StatusProxy(object):
    def __init__(self, username, password):
        self.client = XMPPClient(JID(username), password)
        self.presence = PresenceFetcher()
        self.presence.setHandlerParent(self.client)
        self.client.startService()

    def getStatuses(self, account):
        if isinstance(account, str):
            account = JID(account)
        return self.presence.doProbe(account)

proxy = StatusProxy('thejapanesegeek@gmail.com/Twisted', getpass.getpass())

def makeCall():
    d = proxy.getStatuses('ellie@stillinbeta.com')
    d.addCallback(print)
    return d

LoopingCall(makeCall).start(10)

from twisted.internet import reactor
reactor.run()
