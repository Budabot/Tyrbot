import json
import time
import os
from core.registry import Registry

try:
    config = json.load(open("./conf/config.json", "r"))

    Registry.load_instances(["core", os.path.join("modules", "core"), os.path.join("modules", "standard"), os.path.join("modules", "custom")])
    Registry.inject_all()

    bot = Registry.get_instance("budabot")
    bot.init(config, Registry)
    bot.connect(config["server"]["host"], config["server"]["port"])

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
