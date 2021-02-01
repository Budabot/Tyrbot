from core.decorators import instance
from core.logger import Logger


@instance()
class CommandAliasService:
    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.db = registry.get_instance("db")

    def check_for_alias(self, command_str):
        row = self.get_alias(command_str)
        if row and row.enabled:
            return row.command
        else:
            return None

    def get_alias(self, alias):
        return self.db.query_single("SELECT alias, command, enabled FROM command_alias WHERE alias = ?", [alias])

    def add_alias(self, alias, command, force_enable=False):
        """Call during start"""
        row = self.get_alias(alias)
        if row:
            if row.enabled:
                return False
            elif force_enable:
                self.db.exec("UPDATE command_alias SET command = ?, enabled = 1 WHERE alias = ?", [command, alias])
            return True
        else:
            self.db.exec("INSERT INTO command_alias (alias, command, enabled) VALUES (?, ?, 1)", [alias, command])
            return True

    def remove_alias(self, alias):
        row = self.get_alias(alias)
        if row:
            if row.enabled:
                self.db.exec("UPDATE command_alias SET enabled = 0 WHERE alias = ?", [alias])
                return True
            else:
                return False
        else:
            return False

    def get_enabled_aliases(self):
        return self.db.query("SELECT alias, command FROM command_alias WHERE enabled = 1 ORDER BY alias ASC")
