import json
from budabot import Budabot  # needed for registry to load budabot class
from registry import get_instance, inject_all

config = json.load(open("./conf/config.json", "r"))

inject_all()

bot = get_instance("budabot")
bot.connect("chat.d1.funcom.com", 7105)
bot.login(config["username"], config["password"], config["character"])
bot.run()
