from twisted.application.service import Application

from statusbot.service import StatusBotService

application = Application('statusbot')

statusBot = StatusBotService()
statusBot.setServiceParent(application)
