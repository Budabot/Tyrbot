import re

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
        return cls._registry.get(name, None)

    @classmethod
    def add_instance(cls, name, inst):
        name = cls.format_name(name)
        cls._registry[name] = inst

    @classmethod
    def format_name(cls, name):
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    @classmethod
    def load_instances(cls):
        # needed to load instances
        import core.budabot
        import core.text
