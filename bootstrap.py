from core.registry import Registry
from core import config_creator
from core.dict_object import DictObject
from core.logger import Logger
from core.aochat.mmdb_parser import MMDBParser
import hjson
import time
import os
import platform
import sys


try:
    # load logging configuration
    import conf.logging

    Registry.logger = Logger("core.registry")

    logger = Logger("core.bootstrap")
    logger.info("Starting Tyrbot...")
    config_file = "./conf/config.hjson"

    if sys.version_info < (3, 6):
        logger.error("Python 3.6 is required (3.5 will not work)")
        exit(0)

    if sys.version_info >= (3, 7):
        logger.warning("Python 3.7 is not yet supported; if you run into issues, considering downgrading to Python 3.6")

    # start config wizard if config file does not exist
    if not os.path.exists(config_file):
        config_creator.create_new_cfg(config_file, "./conf/config.template.hjson")

    # load config
    logger.debug("Reading config file '%s'" % config_file)
    with open(config_file, "r") as cfg:
        config = DictObject(hjson.load(cfg))

    # ensure dimension is integer
    if isinstance(config.server.dimension, str):
        config.server.dimension = int(config.server.dimension)

    if platform.system() == "Windows":
        os.system("title %s.%d" % (config.character, config.server.dimension))

    # paths to search for instances: core + module_paths
    paths = ["core"]
    paths.extend(config.module_paths)

    # load instances
    logger.debug("Loading instances")
    Registry.load_instances(paths)
    Registry.inject_all()

    # configure database
    db = Registry.get_instance("db")
    if config.database.type == "sqlite":
        db.connect_sqlite("./data/" + config.database.name)
    elif config.database.type == "mysql":
        db.connect_mysql(config.database.host, config.database.username, config.database.password, config.database.name)
    else:
        raise Exception("Unknown database type '%s'" % config.database.type)

    # run db upgrade scripts
    import upgrade

    # finish initializing bot and modules, and then connect
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
