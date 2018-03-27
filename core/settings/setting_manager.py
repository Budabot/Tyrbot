from core.decorators import instance
from core.logger import Logger
from .setting_types import SettingType
import os


@instance()
class SettingManager:
    def __init__(self):
        self.logger = Logger("setting_manager")
        self.settings = {}
        # self.setting_types = ["text", "options", "number", "time", "color"]

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")

    def start(self):
        self.db.load_sql_file("setting.sql", os.path.dirname(__file__))
        self.db.exec("UPDATE setting SET verified = 0")

    def post_start(self):
        self.db.exec("DELETE FROM event_config WHERE verified = 0")

    def register(self, name, setting_type: SettingType, description, module):
        name = name.lower()
        module = module.lower()

        if not description:
            self.logger.warning("No description specified for setting '%s'" % name)

        row = self.db.query_single("SELECT name, type, value, description "
                                   "FROM setting WHERE name = ?",
                                   [name])

        if row is None:
            # add new event commands
            self.db.exec(
                "INSERT INTO setting (name, type, value, description, module, verified) VALUES "
                "(?, ?, ?, ?, ?, ?)",
                [name, setting_type, setting_type.get_value(), description, module, 1])
        else:
            # mark command as verified
            self.db.exec(
                "UPDATE setting SET description = ?, verified = ?, module = ? WHERE name = ?",
                [description, 1, module, name])

        self.settings[name] = {"type": setting_type}

    def get(self, name):
        name = name.lower()
        row = self.db.query_single("SELECT value FROM setting WHERE name = ?", [name])
        setting = self.settings.get(name, None)
        if row and setting:
            setting_type = setting["type"]
            setting_type.set_value(row.value)
            return setting_type
        else:
            return None

    def set(self, name, value):
        name = name.lower()
        setting = self.settings.get(name, None)
        if setting:
            setting_type = setting["type"]
            setting_type.set_value(value)
            self.db.exec("UPDATE setting SET value = ? WHERE name = ?", [setting_type.get_value(), name])
