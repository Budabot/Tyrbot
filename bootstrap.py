import json
from core.registry import Registry

config = json.load(open("./conf/config.json", "r"))

Registry.inject_all()

bot = Registry.get_instance("budabot")
bot.connect("chat.d1.funcom.com", 7105)
bot.login(config["username"], config["password"], config["character"])
bot.run()
