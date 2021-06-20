import itertools
from core.dict_object import DictObject


def flatmap(func, *iterable):
    return itertools.chain.from_iterable(map(func, *iterable))


# taken from: https://stackoverflow.com/a/8529229/280574 and modified
def get_attrs(obj):
    attrs = {}
    for cls in obj.__class__.__mro__:
        attrs.update(cls.__dict__.items())
    attrs.update(obj.__class__.__dict__.items())
    return attrs


def get_config_from_env(env_dict, logger):
    config_obj = DictObject()
    for k, v in env_dict.items():
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
