import inspect

from core.decorators import instance
from core.logger import Logger
from .setting_types import SettingType
from core.registry import Registry
from core.functions import get_attrs


@instance()
class SettingService:
    def __init__(self):
        self.logger = Logger(__name__)
        self.settings = {}
        self.db_cache = {}
        self.change_listeners = {}

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")

    def start(self):
        # process decorators
        for _, inst in Registry.get_all_instances().items():
            for name, method in get_attrs(inst).items():
                if hasattr(method, "setting"):
                    setting_name, value, description, extended_description, obj = getattr(method, "setting")
                    self.register(setting_name, value, description, obj, inst.module_name, extended_description)

    def register(self, name, value, description, setting: SettingType, module, extended_description=None):
        """Deprecated. Use register_new()"""
        self.logger.warning(f"Using deprecated register method for setting '{name}' in module {module}")
        self.register_new(module, name, value, setting, description, extended_description)

    def register_new(self, module, name, value, setting: SettingType, description, extended_description=None):
        """Call during start"""
        name = name.lower()
        module = module.lower()
        setting.set_name(name)
        setting.set_description(description)
        setting.set_extended_description(extended_description)

        if not description:
            self.logger.warning("No description specified for setting '%s'" % name)

        if " " in name:
            raise Exception("One or more spaces found in setting name '%s' for module '%s'" % (name, module))

        row = self.db.query_single("SELECT name, value, description FROM setting WHERE name = ?", [name])

        if row is None:
            self.logger.debug("Adding setting '%s'" % name)

            self.db.exec(
                "INSERT INTO setting (name, value, description, module, verified) VALUES (?, ?, ?, ?, ?)",
                [name, "", description, module, 1])

            # verify default value is a valid value, and is formatted appropriately
            setting.set_value(value)
        else:
            self.logger.debug("Updating setting '%s'" % name)
            self.db.exec(
                "UPDATE setting SET description = ?, verified = ?, module = ? WHERE name = ?",
                [description, 1, module, name])

        self.settings[name] = setting

    def register_change_listener(self, setting_name, handler):
        """
        Call during start

        Args:
            setting_name: str
            handler: (name: string, old_value, new_value) -> void
        """

        if len(inspect.signature(handler).parameters) != 3:
            raise Exception("Incorrect number of arguments for handler '%s.%s()'" % (handler.__module__, handler.__name__))

        if setting_name in self.settings:
            if setting_name not in self.change_listeners:
                self.change_listeners[setting_name] = []
            self.change_listeners[setting_name].append(handler)
        else:
            raise Exception("Could not register change_listener for setting '%s' since it does not exist" % setting_name)

    def get_value(self, name):
        # check cache first
        result = self.db_cache.get(name, None)
        if result:
            return result.value
        else:
            row = self.db.query_single("SELECT value FROM setting WHERE name = ?", [name])

            # store result in cache
            self.db_cache[name] = row

            return row.value if row else None

    def set_value(self, name, value):
        old_value = self.get_value(name)

        # clear cache
        self.db_cache[name] = None

        self.db.exec("UPDATE setting SET value = ? WHERE name = ?", [value, name])

        if name in self.change_listeners:
            for change_listener in self.change_listeners[name]:
                change_listener(name, old_value, value)

    def get(self, name):
        name = name.lower()
        setting = self.settings.get(name, None)
        if setting:
            return setting
        else:
            return None
