This is a jabber bot that tweets someone's Jabber statuses (presences),
because Reasons.

It's implemented in Twisted, you can check requirements.txt for a full
prerequisite list.

The app checks twitter at a (configurable) interval, then posts the latest
status it found. It is (I am) lazy and it relies on the fact that Twitter
won't let you post duplicate tweets.

You'll need both a registered twitter [app][twitter] and token to make this
work. Copy the config.pysample file to config.py, then fill in your
CONSUMER\_TOKEN and CONSUMER\_SECRET. You can then run `get_auth.py` to
get an ACCESS\_TOKEN and ACCESS\_SECRET.

I've not been able to find any other examples of interacting with Twitter
using Twisted, so perhaps that will be useful to someone.

[twitter]: https://dev.twitter.com/apps

