def instance(cls):
    Registry.add_instance(cls.__name__, cls())
    return cls


class Registry:
    _registry = {}

    @classmethod
    def inject_all(cls):
        from budabot import Budabot  # needed to load budabot class
        for key in cls._registry:
            cls._registry[key].inject(cls)

    @classmethod
    def get_instance(cls, name):
        if name.lower() in cls._registry:
            return cls._registry[name.lower()]
        else:
            return None

    @classmethod
    def add_instance(cls, name, inst):
        cls._registry[name.lower()] = inst
