from core.decorators import instance
from core.logger import Logger


@instance()
class SettingManager:
    def __init__(self):
        self.logger = Logger("setting_manager")
        self.setting_types = ["text", "options", "number", "time", "color"]

    def inject(self, registry):
        self.db = registry.get_instance("db")

    def start(self):
        self.db.load_sql_file("./core/config/setting.sql")
        self.db.exec("UPDATE setting SET verified = 0")

    def post_start(self):
        self.db.exec("DELETE FROM event_config WHERE verified = 0")

    def register(self, name, setting_type, value, description):
        setting_type = setting_type.lower()

        if setting_type not in self.setting_types:
            self.logger.error("Could not register setting '%s' for setting type '%s': setting type does not exist"
                              % (name, setting_type))
            return

        row = self.db.query_single("SELECT name, type, setting, description "
                                   "FROM setting WHERE name = ?",
                                   [name])

        if row is None:
            # add new event config
            self.db.exec(
                "INSERT INTO setting (name, type, setting, description, verified) VALUES "
                "(?, ?, ?, ?, ?)",
                [name, setting_type, value, description, 1])
        else:
            # mark command as verified
            if setting_type == row.type:
                # if type has not changed, update description
                self.db.exec(
                    "UPDATE setting SET description = ?, verified = ? WHERE name = ?",
                    [description, 1, name])
            else:
                # if type has changed, also update type and setting value
                self.db.exec(
                    "UPDATE setting SET type = ?, setting = ?, description = ?, verified = ? WHERE name = ?",
                    [setting_type, value, description, 1, name])

    def get(self, name):
        row = self.db.query_single("SELECT setting FROM setting WHERE name = ?", [name])
        if row:
            return row.setting
        else:
            return None
