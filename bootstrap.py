from core.dict_object import DictObject
from core.feature_flags import FeatureFlags
from core.registry import Registry
from core import config_creator
from core.logger import Logger
from core.aochat.mmdb_parser import MMDBParser
from core.functions import get_config_from_env
from upgrade import run_upgrades
import time
import os
import platform
import sys


try:
    # load logging configuration
    import conf.logging

    Registry.logger = Logger("core.registry")

    with open("version.txt", "r") as f:
        version = f.read().strip()

    logger = Logger("core.bootstrap")
    logger.info(f"Starting Tyrbot {version} with Python {platform.python_version()}")
    config_file = "./conf/config.py"

    if sys.version_info < (3, 9):
        logger.error(f"Python 3.9 or greater is recommended. Consider upgrading your Python version if you have issues. Current Python version: {platform.python_version()}")

    # load template config file as a base set of defaults
    from conf.config_template import config as template_config

    # load config values from env vars
    env_config = get_config_from_env(os.environ, logger)
    if env_config:
        # converts dicts to lists
        if "bots" in env_config and isinstance(env_config.bots, dict):
            env_config.bots = list(env_config.bots.values())

        if "module_paths" in env_config and isinstance(env_config.module_paths, dict):
            env_config.module_paths = list(env_config.module_paths.values())

        # shallow merge of template and env configs
        config = DictObject({**template_config, **env_config})
        logger.info("Reading config from env vars")
    else:
        # start config wizard if config file does not exist
        if not os.path.exists(config_file):
            config_creator.create_new_cfg(config_file, template_config)

        # load config
        logger.info("Reading config from file '%s'" % config_file)
        from conf.config import config

    if "bots" not in config:
        raise Exception("No bots detected in config")

    if not config.bots[0].is_main:
        raise Exception("First bot must be configured as a main bot")

    # ensure dimension is integer
    if isinstance(config.server.dimension, str):
        config.server.dimension = int(config.server.dimension)

    # set feature flags
    if "features" in config:
        for k, v in config.features.items():
            k = k.upper()
            logger.info("Feature %s: %s" % (k, v))
            setattr(FeatureFlags, k, v)

    if platform.system() == "Windows":
        os.system("title %s.%d" % (config.bots[0].character, config.server.dimension))

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
        db.connect_mysql(config.database.host, config.database.port, config.database.username, config.database.password, config.database.name)
    else:
        raise Exception("Unknown database type '%s'" % config.database.type)

    # run db upgrade scripts
    run_upgrades()

    # finish initializing bot and modules, and then connect
    bot = Registry.get_instance("bot")
    bot.version = version
    bot.init(config, Registry, MMDBParser("text.mdb"))

    if not bot.connect(config):
        bot.disconnect()
        time.sleep(5)
        exit(3)
    else:
        status = bot.run()
        bot.disconnect()
        exit(status.value)
except KeyboardInterrupt:
    # TODO set bot.status = BotStatus.SHUTDOWN, then bot.disconnect()
    logger = Logger("core.bootstrap")
    logger.info("keyboard interrupt detected, shutting down")
    exit(0)
except Exception as e:
    logger = Logger("core.bootstrap")
    logger.error("", e)
    # TODO set bot.status = BotStatus.Error, then bot.disconnect()
    exit(4)
