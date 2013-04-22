from __future__ import print_function

import logging

import oauth2 as oauth
from twisted.internet.defer import Deferred
from twisted.python import log
from twisted.words.protocols.jabber.jid import JID
from wokkel.client import XMPPClient
from wokkel.xmppim import PresenceProtocol

class PresenceFetcher(PresenceProtocol):
    RECIEVE_FOR_SECS = 5

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
        jobState = self.statusJobs.get(userhost)
        if not jobState:
            log.msg("Received status after results sent",
                    logLevel=logging.WARNING)
        else:
            jobState.statuses |= {s for s in presence.statuses.values() if s}

    def doProbe(self, account):
        if isinstance(account, str):
            account = JID(account)
        d = Deferred()

        from twisted.internet import reactor
        reactor.callLater(self.RECIEVE_FOR_SECS,
                          self.sendResults,
                          account.userhost())
        self.statusJobs[account.userhost()] = self.StatusJobState(d)
        self.probe(account)
        return d

class StatusProxy(object):
    def __init__(self, username, password, host='talk.google.com'):
        self.client = XMPPClient(JID(username), password,host)
        self.presence = PresenceFetcher()
        self.presence.setHandlerParent(self.client)
        self.client.startService()

    def getStatuses(self, account):
        if isinstance(account, str):
            account = JID(account)
        return self.presence.doProbe(account)
