from __future__ import print_function

import oauth2 as oauth
import json
import urllib
import logging

from twisted.internet.defer import succeed, fail, Deferred, DeferredList
from twisted.python import log
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer
from zope.interface.declarations import implements

from statusbot.longurl import Longifyer
from statusbot.common import receive_response
from statusbot import config

# User-specific
ACCESS_TOKEN = oauth.Token(key=config.ACCESS_KEY, secret=config.ACCESS_SECRET)

# Application-specific
CONSUMER = oauth.Consumer(config.CONSUMER_KEY, config.CONSUMER_SECRET)


class Tweeter(object):
    TWEET_URL = "https://api.twitter.com/1.1/statuses/update.json"
    TIMELINE_URL = "https://api.twitter.com/1.1/statuses/user_timeline.json"
    PREVIOUS_TWEET_COUNT = 10
    FAILED_RESPONSE_RETRY_SECS = 10

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

    def __init__(self):
        from twisted.internet import reactor
        self.agent = Agent(reactor)
        self.signature_method = oauth.SignatureMethod_HMAC_SHA1()
        self.previous_tweets = None

        # If we receive tweets before we fetch the old ones, queue them up
        # to be run later
        self.tweet_queue = []
        self.longify = Longifyer()

        self.get_previous_tweets()


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
        if self.previous_tweets is None:
            d = Deferred()
            d.addCallback(self.tweet)
            self.tweet_queue = d, status
            return d
        elif status in self.previous_tweets:
            log.msg('Already tweeted "{}"'.format(status),
                    logLevel=logging.WARNING)
            return succeed(('5xx', 'Duplicate tweet'))

        parameters = {'status': status}
        auth_body = self._getAuthorization(parameters)
        headers = {'content-type': ['application/x-www-form-urlencoded']}
        d = self.agent.request('POST', self.TWEET_URL,
                               headers=Headers(headers),
                               bodyProducer=self.StringProducer(auth_body))
        d.addCallback(receive_response)
        # If it's a success, save it.
        d.addCallback(self._save_tweeted)
        return d

    def _save_tweeted(self, response, status):
        self.previous_tweets.add(status)
        # Pass through the response
        return response

    def get_previous_tweets(self):
        params = {'trim_user': True, 'count': self.PREVIOUS_TWEET_COUNT}

        req = oauth.Request.from_consumer_and_token(
            consumer=CONSUMER,
            token=ACCESS_TOKEN,
            http_method='GET',
            http_url=self.TIMELINE_URL,
            parameters=params)
        req.sign_request(self.signature_method,
                         token=ACCESS_TOKEN,
                         consumer=CONSUMER)

        d = self.agent.request('GET', str(req.to_url()))
        d.addErrback(self._retry_on_failure)
        d.addCallback(receive_response)
        d.addCallback(self._lengthen_tweets)
        d.addCallback(self._send_queued_tweets)
        return d

    def _retry_on_failure(self, failure):
        log.err(failure, "Failed to receive previous tweets, trying again in "
                "{}  seconds".format(self.FAILED_RESPONSE_RETRY_SECS))

        from twisted.internet import reactor
        reactor.callLater(self.FAILED_RESPONSE_RETRY_SECS,
                          self.get_previous_tweets)

    def _lengthen_tweets(self, response):
        code, tweet_json = response
        call_later = False
        if code != 200:
            return fail(IOError(
                "Received response code {}: {}".format(code, tweet_json)))
        try:
            previous_tweets = {tweet['text'] for tweet
                                             in json.loads(tweet_json)}
            log.msg("Previous tweets: {}".format(self.previous_tweets))

        except (KeyError, ValueError):
            return fail()
        dl = DeferredList([self.longify.replace_all(tweet)
                           for tweet in previous_tweets])
        dl.addCallback(self._save_tweets)

    def _save_tweets(self, tweets):
        self.previous_tweets = {tweet for status, tweet in tweets}
        log.msg("Lengthed tweets: {}".format(self.previous_tweets))

    def _send_queued_tweets(self, _):
        while self.tweet_queue:
            d, status = self.tweet_queue.pop()
            d.callback(status)
