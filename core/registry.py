import re
import os
import importlib


class Registry:
    _registry = {}

    @classmethod
    def inject_all(cls):
        cls.load_instances()

        # inject registry so instance can get references to other instances
        for key in cls._registry:
            try:
                cls._registry[key].inject
            except AttributeError:
                pass
            else:
                cls._registry[key].inject(cls)

    @classmethod
    def start_all(cls):
        # call start() on instances so they can finish any init() processes
        for key in cls._registry:
            try:
                cls._registry[key].start
            except AttributeError:
                pass
            else:
                cls._registry[key].start()

    @classmethod
    def get_instance(cls, name):
        return cls._registry.get(name, None)

    @classmethod
    def get_all_instances(cls):
        return cls._registry

    @classmethod
    def add_instance(cls, name, inst):
        name = cls.format_name(name)
        cls._registry[name] = inst

    @classmethod
    def format_name(cls, name):
        # camel-case to snake-case
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    @classmethod
    def load_instances(cls):
        for directory in ["core", "modules\\whereis"]:
            cls.load_modules_from_dir(directory)

    @classmethod
    def load_modules_from_dir(cls, directory):
        for name in os.listdir(directory):
            if name.endswith(".py") and name != "__init__.py":
                # strip the extension
                module = name[:-3]
                importlib.import_module(directory.replace("\\", ".") + "." + module)
