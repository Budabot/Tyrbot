def instance(cls):
    Registry.add_instance(cls.__name__, cls())
    return cls


class Registry:
    _registry = {}

    @classmethod
    def inject_all(cls):
        cls.load_instances()

        # inject registry so instance can get references to other instances
        for key in cls._registry:
            cls._registry[key].inject(cls)

        # call start() on instances so they can finish any init() processes
        for key in cls._registry:
            cls._registry[key].start()

    @classmethod
    def get_instance(cls, name):
        return cls._registry.get(name.lower(), None)

    @classmethod
    def add_instance(cls, name, inst):
        cls._registry[name.lower()] = inst

    @classmethod
    def load_instances(cls):
        from budabot import Budabot  # needed to load budabot class