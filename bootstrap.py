from core.registry import Registry
from core import config_creator
from core.map_object import MapObject
from core.logger import Logger
from core.aochat.mmdb_parser import MMDBParser
import logging
import sys
import hjson
import time
import os


try:
    Logger.add_logger(logging.handlers.RotatingFileHandler("./logs/bot.log", maxBytes=5 * 1024 * 1024 * 1024, backupCount=1000, encoding="utf-8"))
    Logger.add_logger(logging.StreamHandler(sys.stdout))
    Registry.logger = Logger("registry")

    logger = Logger("bootstrap")
    logger.info("Starting Tyrbot...")
    config_file = "./conf/config.hjson"

    if not os.path.exists(config_file):
        config_creator.create_new_cfg(config_file, "./conf/config.template.hjson")

    logger.debug("Reading config file '%s'" % config_file)
    with open(config_file, "r") as cfg:
        config = MapObject(hjson.load(cfg))

    # paths to search for instances: core + module_paths
    paths = ["core"]
    paths.extend(config.module_paths)

    logger.debug("Loading instances")
    Registry.load_instances(paths)
    Registry.inject_all()

    bot = Registry.get_instance("bot")
    bot.init(config, Registry, paths, MMDBParser("text.mdb"))
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
