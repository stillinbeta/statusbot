import json

from twisted.application import service
from twisted.internet.defer import succeed
from twisted.internet.task import LoopingCall
from twisted.python import log
from twisted.words.protocols.jabber.jid import JID
from wokkel.client import XMPPClient

from statusbot import config
from statusbot.presence import PresenceFetcher
from statusbot.twitter import Tweeter

class StatusBotService(service.Service):
    def __init__(self):
        self.client = XMPPClient(JID(config.JABBER_CLIENT_USER),
                                 config.JABBER_CLIENT_PASS,
                                 config.JABBER_CLIENT_HOST)
        self.presenceFetcher = PresenceFetcher()
        self.presenceFetcher.setHandlerParent(self.client)
        self.tweeter = Tweeter()
        self.loopingCall = LoopingCall(self.makeRequest)

    def startService(self):
        service.Service.startService(self)
        self.client.startService()
        self.loopingCall.start(config.REFRESH_INTERVAL_SECS)

    def stopService(self):
        service.Service.stopService(self)
        self.loopingCall.stop()
        self.client.stopService()

    def makeRequest(self):
        d = self.presenceFetcher.doProbe(config.JABBER_TARGET)
        d.addCallbacks(self._sendTweet, log.err)
        return d

    def _sendTweet(self, statuses):
        if not statuses:
            log.msg("No statuses received")
            return succeed(None)
        else:
            d = self.tweeter.tweet(statuses[0])
            d.addCallback(self._receiveTweetResponse)
            return d

    def _receiveTweetResponse(self, result):
        code, body = result
        body = json.loads(body)
        # 403 is probably a duplicate tweet
        if code == 200:
            log.msg("Tweeted new status: " + body['text'])
        elif code == 403:
            log.msg("Duplicate tweet, ignoring")
        else:
            log.err("Error tweeting {}: {}".format(code, body))
