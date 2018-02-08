import json
from bot import Bot

config = json.load(open("./conf/config.json", "r"))

bot = Bot()
bot.connect("chat.d1.funcom.com", 7105)
bot.login(config["username"], config["password"], config["character"])
