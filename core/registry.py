import re
import os
import importlib
import itertools


class Registry:
    _registry = {}

    @classmethod
    def inject_all(cls):
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
    def load_instances(cls, parent_dirs):
        # get all subdirectories
        dirs = cls.flatmap(lambda x: os.walk(x), parent_dirs)
        dirs = filter(lambda y: not y[0].endswith("__pycache__"), dirs)

        def get_files(tup):
            return map(lambda x: tup[0] + "\\" + x, tup[2])

        # get files from subdirectories
        files = cls.flatmap(get_files, dirs)
        files = filter(lambda z: z.endswith(".py") and not z.endswith("__init__.py"), files)

        # load files as modules
        for file in files:
            cls.load_module(file)

    @classmethod
    def load_module(cls, file):
        # strip the extension
        file = file[:-3]
        importlib.import_module(file.replace("\\", "."))

    @classmethod
    def flatmap(cls, func, *iterable):
        return itertools.chain.from_iterable(map(func, *iterable))
