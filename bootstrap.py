from core.registry import Registry
from core import config_creator
from core.map_object import MapObject
import json
import time
import os


try:
    config_file = "./conf/config.json"

    if not os.path.exists(config_file):
        config_creator.create_new_cfg(config_file)

    with open(config_file, "r") as cfg:
        config = MapObject(json.load(cfg))

    Registry.load_instances(["core", os.path.join("modules", "core"), os.path.join("modules", "standard"), os.path.join("modules", "custom")])
    Registry.inject_all()

    bot = Registry.get_instance("budabot")
    bot.init(config, Registry)
    bot.connect(config.server.host, config.server.port)

    if not bot.login(config.username, config.password, config.character):
        bot.disconnect()
        time.sleep(5)
        exit(1)
    else:
        status = bot.run()
        bot.disconnect()
        exit(status.value)
except KeyboardInterrupt:
    exit(0)
