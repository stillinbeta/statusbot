# -*- coding: utf-8 -*-
from __future__ import print_function

import re
import json
import urllib
import sys

from twisted.internet.defer import DeferredList
from twisted.python.failure import Failure
from twisted.python import log
from twisted.web.client import Agent
from twisted.web.http_headers import Headers

from statusbot.common import receive_response

class Longifyer(object):
    EXPAND_URL = 'http://api.longurl.org/v2/expand?format=json'
    # http://stackoverflow.com/questions/520031
    find_urls = re.compile(r"""((?:[a-z][\w-]+:(?:/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.‌​][a-z]{2,4}/)(?:[^\s()<>]+|(([^\s()<>]+|(([^\s()<>]+)))*))+(?:(([^\s()<>]+|(‌​([^\s()<>]+)))*)|[^\s`!()[]{};:'".,<>?«»“”‘’]))""", re.DOTALL)

    def __init__(self):
        from twisted.internet import reactor
        self.agent = Agent(reactor)

    def lengthen_url(self, short_url):
        req_url = self.EXPAND_URL + '&' + urllib.urlencode({'url': short_url})
        d = self.agent.request('GET', req_url)
        d.addCallback(receive_response)
        d.addCallback(self._decode_response)
        return d

    def _decode_response(self, response):
        code, body = response
        if code != 200:
            return Failure(IOError("Got invalid response {}".format(code)))
        try:
           decoded =  json.loads(body)
           return decoded['long-url']
        except ValueError:
            return Failure()
        except KeyError:
            return Failure(KeyError("Malformed response {}".format(decoded)))

    def replace_all(self, string):
        urls = self.find_urls.findall(string)
        # Concat the matched tuples
        urls = [''.join(url) for url in urls]
        d = DeferredList([self.lengthen_url(url) for url in urls])
        d.addCallback(self._replace_all_cb, urls, string)
        return d

    def _replace_all_cb(self, long_urls, short_urls, string):
        for (success, long_url), short_url in zip(long_urls, short_urls):
            if not success:
                log.err(long_url, "Couldn't shorten URL {}".format(short_url))
            else:
                try:
                    string = string.replace(short_url, long_url)
                except Exception as e:
                    raise

        return string

if __name__ == "__main__":
    log.startLogging(sys.stderr)
    l = Longifyer()
    d = l.replace_all(u"https://t.co/HK2PLPoQF2 http://t.co/r3gXGYgIQ2 http://google.com")
    d.addCallbacks(print, log.err)

    from twisted.internet import reactor
    reactor.run()
