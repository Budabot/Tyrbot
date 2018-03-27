from core.decorators import instance
from core.logger import Logger
import os


@instance()
class SettingManager:
    def __init__(self):
        self.logger = Logger("setting_manager")
        self.setting_types = ["text", "options", "number", "time", "color"]

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")

    def start(self):
        self.db.load_sql_file("setting.sql", os.path.dirname(__file__))
        self.db.exec("UPDATE setting SET verified = 0")

    def post_start(self):
        self.db.exec("DELETE FROM event_config WHERE verified = 0")

    def register(self, name, setting_type, value, description, module):
        name = name.lower()
        setting_type = setting_type.lower()
        module = module.lower()

        if setting_type not in self.setting_types:
            self.logger.error("Could not register setting '%s' for setting type '%s': setting type does not exist"
                              % (name, setting_type))
            return

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
                [name, setting_type, value, description, module, 1])
        else:
            # mark command as verified
            if setting_type == row.type:
                # if type has not changed, update description
                self.db.exec(
                    "UPDATE setting SET description = ?, verified = ?, module = ? WHERE name = ?",
                    [description, 1, module, name])
            else:
                # if type has changed, also update type and setting value
                self.db.exec(
                    "UPDATE setting SET type = ?, value = ?, description = ?, verified = ?, module = ? WHERE name = ?",
                    [setting_type, value, description, 1, module, name])

    def get(self, name):
        name = name.lower()
        row = self.db.query_single("SELECT value FROM setting WHERE name = ?", [name])
        if row:
            return row.value
        else:
            return None
