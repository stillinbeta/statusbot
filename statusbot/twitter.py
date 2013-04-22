from __future__ import print_function

import oauth2 as oauth
import urllib

from twisted.internet.defer import succeed, fail, Deferred
from twisted.internet.protocol import Protocol
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer
from zope.interface.declarations import implements

from statusbot import config

# User-specific
ACCESS_TOKEN = oauth.Token(key=config.ACCESS_KEY, secret=config.ACCESS_SECRET)

# Application-specific
CONSUMER = oauth.Consumer(config.CONSUMER_KEY, config.CONSUMER_SECRET)

class Tweeter(object):
    TWEET_URL = "http://api.twitter.com/1.1/statuses/update.json"

    class StringProducer(object):
        implements(IBodyProducer)

        def __init__(self, body):
            self.body = body
            self.length = len(body)

        def startProducing(self, consumer):
            consumer.write(self.body)
            return succeed(None)

        def pauseProducing(self):
            pass

        def stopProducing(self):
            pass

        def resumeProducing(self):
            pass

    class SimpleReceiver(Protocol):
        def __init__(self, deferred, code):
            self.buf = ''
            self.deferred = deferred
            self.code = code

        def dataReceived(self, data):
            self.buf += data

        def connectionLost(self, reason):
            self.deferred.callback((self.code, self.buf))

    def __init__(self):
        from twisted.internet import reactor
        self.agent = Agent(reactor)
        self.signature_method = oauth.SignatureMethod_HMAC_SHA1()

    def _getAuthorization(self, parameters):
        req = oauth.Request.from_consumer_and_token(
            consumer=CONSUMER,
            token=ACCESS_TOKEN,
            http_method='POST',
            http_url=self.TWEET_URL,
            parameters=parameters,
            is_form_encoded=True
            )

        req.sign_request(self.signature_method,
                         token=ACCESS_TOKEN,
                         consumer=CONSUMER)
        return req.to_postdata()

    def tweet(self, status):
        parameters = {'status': status}
        auth_body = self._getAuthorization(parameters)
        headers = {'content-type': ['application/x-www-form-urlencoded']}
        d = self.agent.request('POST', self.TWEET_URL,
                               headers=Headers(headers),
                               bodyProducer=self.StringProducer(auth_body))
        d.addCallback(self._receive_response)
        return d

    def _receive_response(self, response):
        d = Deferred()
        response.deliverBody(self.SimpleReceiver(d, response.code))
        return d
