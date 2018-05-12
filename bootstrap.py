from core.registry import Registry
from core import config_creator
from core.map_object import MapObject
from core.logger import Logger
from core.aochat.mmdb_parser import MMDBParser
import logging
import sys
import json
import time
import os


try:
    mmdb = MMDBParser("text.mdb")

    Logger.add_logger(logging.handlers.RotatingFileHandler("./logs/bot.log", maxBytes=5 * 1024 * 1024 * 1024, backupCount=1000))
    Logger.add_logger(logging.StreamHandler(sys.stdout))
    Registry.logger = Logger("registry")

    logger = Logger("bootstrap")
    logger.info("Starting Budabot...")
    config_file = "./conf/config.json"

    if not os.path.exists(config_file):
        config_creator.create_new_cfg(config_file)

    logger.debug("Reading config file '%s'" % config_file)
    with open(config_file, "r") as cfg:
        config = MapObject(json.load(cfg))

    logger.debug("Loading instances")
    Registry.load_instances(["core", os.path.join("modules", "core"), os.path.join("modules", "standard"), os.path.join("modules", "custom")])
    Registry.inject_all()

    bot = Registry.get_instance("budabot")
    bot.init(config, Registry)
    bot.connect(config.server.host, config.server.port)

    if not bot.login(config.username, config.password, config.character):
        bot.disconnect()
        time.sleep(5)
        exit(3)
    else:
        status = bot.run()
        bot.disconnect()
        exit(status.value)
except KeyboardInterrupt:
    exit(0)
except Exception as e:
    logger = Logger("bootstrap")
    logger.error("", e)
    exit(4)
