import json
from budabot import Budabot

config = json.load(open("./conf/config.json", "r"))

bot = Budabot()
bot.connect("chat.d1.funcom.com", 7105)
bot.login(config["username"], config["password"], config["character"])
bot.run()