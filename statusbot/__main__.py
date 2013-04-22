from statusbot.service import StatusBotService

statusBot = StatusBotService()
statusBot.startService()

from twisted.internet import reactor
reactor.run()
