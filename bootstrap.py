import json
import time
import os
from core.registry import Registry

try:
    config = json.load(open("./conf/config.json", "r"))

    Registry.load_instances(["core", os.path.join("modules", "core"), os.path.join("modules", "user"), os.path.join("modules", "extra")])
    Registry.inject_all()

    db = Registry.get_instance("db")
    db.connect(config["database"]["name"])

    Registry.start_all()

    bot = Registry.get_instance("budabot")
    bot.superadmin = config["superadmin"].capitalize()
    bot.connect("chat.d1.funcom.com", 7105)
    bot.post_start()

    if not bot.login(config["username"], config["password"], config["character"]):
        bot.disconnect()
        time.sleep(5)
        exit(1)
    else:
        status = bot.run()
        bot.disconnect()
        exit(status.value)
except KeyboardInterrupt:
    exit(0)
