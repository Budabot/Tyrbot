from core.feature_flags import FeatureFlags
from core.registry import Registry
from core import config_creator
from core.dict_object import DictObject
from core.logger import Logger
from core.aochat.mmdb_parser import MMDBParser
from core.functions import merge_dicts
from upgrade import run_upgrades
import hjson
import time
import os
import platform
import sys


def get_config_from_env():
    config_obj = DictObject()
    for k, v in os.environ.items():
        if k.startswith("TYRBOT_"):
            keys = k[7:].lower().split("_")
            temp_config = config_obj
            for key in keys[:-1]:
                key = key.replace("-", "_")
                # create key if it doesn't already exist
                if key not in temp_config:
                    temp_config[key] = DictObject()
                temp_config = temp_config.get(key)
            logger.debug("overriding config value from env var '%s'" % k)
            if v.lower() == "true":
                v = True
            elif v.lower() == "false":
                v = False
            temp_config[keys[-1].replace("-", "_")] = v
    return config_obj


try:
    # load logging configuration
    import conf.logging

    Registry.logger = Logger("core.registry")

    logger = Logger("core.bootstrap")
    logger.info("Starting Tyrbot...")
    template_config_file = "./conf/config.template.hjson"
    config_file = "./conf/config.hjson"

    if sys.version_info < (3, 6):
        logger.error("Python 3.6 is required (3.5 will not work)")
        exit(0)

    if (3, 8) <= sys.version_info < (3, 9):
        logger.warning("Python 3.8 has known issues with Tyrbot. If you have issues with the discord module or the websocket relay, "
                       "or if you see SSL errors in the logs, consider downgrading to Python 3.6 or upgrading to Python 3.9")

    # load template config file as a base set of defaults
    with open(template_config_file, "r") as cfg:
        config = DictObject(hjson.load(cfg))

    # load config values from env vars
    env_config = get_config_from_env()
    if env_config:
        config = merge_dicts(config, env_config)
        logger.info("Reading config from env vars")
    else:
        # start config wizard if config file does not exist
        if not os.path.exists(config_file):
            config_creator.create_new_cfg(config_file, template_config_file)

        # load config
        logger.info("Reading config from file '%s'" % config_file)
        with open(config_file, "r") as cfg:
            config = DictObject(hjson.load(cfg))

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
        # TODO compatibility
        if "port" not in config.database:
            config.database.port = 3306
        db.connect_mysql(config.database.host, config.database.port, config.database.username, config.database.password, config.database.name)
    else:
        raise Exception("Unknown database type '%s'" % config.database.type)

    # run db upgrade scripts
    run_upgrades()

    # finish initializing bot and modules, and then connect
    bot = Registry.get_instance("bot")
    bot.init(config, Registry, paths, MMDBParser("text.mdb"))

    if not bot.connect(config):
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
