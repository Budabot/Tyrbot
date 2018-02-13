from core.registry import Registry


def instance(cls):
    Registry.add_instance(cls.__name__, cls())
    return cls
