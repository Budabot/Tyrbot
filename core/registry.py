import re
import os
import importlib
from core.functions import flatmap


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
    def pre_start_all(cls):
        # call pre_start() on instances so they can start any init() processes
        for key in cls._registry:
            try:
                cls._registry[key].pre_start
            except AttributeError:
                pass
            else:
                cls._registry[key].pre_start()

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
    def get_instance(cls, name, is_optional=False):
        instance = cls._registry.get(name)
        if instance or is_optional:
            return instance
        else:
            raise Exception("Missing required dependency '%s'" % name)

    @classmethod
    def get_all_instances(cls):
        return cls._registry

    @classmethod
    def add_instance(cls, name, inst, override=False):
        name = cls.format_name(name)

        inst.module_name = Registry.get_module_name(inst)
        inst.module_dir = Registry.get_module_dir(inst)

        if not override and name in cls._registry:
            raise Exception("Overriding '%s' with new instance" % name)
        elif override and name not in cls._registry:
            raise Exception("No instance '%s' to override" % name)
        cls._registry[name] = inst

    @classmethod
    def format_name(cls, name):
        # camel-case to snake-case
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    @classmethod
    def load_instances(cls, parent_dirs):
        # get all subdirectories
        dirs = flatmap(lambda x: os.walk(x, followlinks=True), parent_dirs)
        dirs = filter(lambda y: not y[0].endswith("__pycache__"), dirs)

        def get_files(tup):
            return map(lambda x: os.path.join(tup[0], x), tup[2])

        # get files from subdirectories
        files = flatmap(get_files, dirs)
        files = filter(lambda z: z.endswith(".py") and not z.endswith("__init__.py"), files)

        # load files as modules
        for file in files:
            cls.load_module(file)

    @classmethod
    def load_module(cls, file):
        # strip the extension
        file = file[:-3]
        importlib.import_module(file.replace("\\", ".").replace("/", "."))

    @classmethod
    def get_module_name(cls, inst):
        parts = inst.__module__.split(".")
        if parts[0] == "core":
            return "core"
        # TODO use values from config module_paths to be more accurate here
        # last name in directory path should be first part, then the next name should be last part
        elif parts[0] == "modules":
            return parts[1] + "." + parts[2]
        else:
            return ".".join(parts[:-1])

    @classmethod
    def get_module_dir(cls, inst):
        parts = inst.__module__.split(".")
        return "." + os.sep + os.sep.join(parts[:-1])

    @classmethod
    def clear(cls):
        cls._registry = {}
