from core.decorators import instance


@instance()
class CommandManager:
    def __init__(self):
        self.db = None

    def inject(self, registry):
        self.db = registry.get_instance("db")

    def register(self, module, handler, channels, command, access_levels, description, help_topic, default_status):
        for (channel, access_level) in zip(channels, access_levels):
            row = self.db.query_single("SELECT 1 FROM command WHERE cmd = ? AND channel = ?", command, channel)
            if row:
                sql = """
                    UPDATE command_<myname> SET module = ?, handler = ?, description = ?, help = ?
                    WHERE cmd = ? AND channel = ?
                """
                self.db.exec(sql, [module, handler, description, help_topic, command, channel])
            else:
                sql = """
                    INSERT INTO command_<myname> (module, handler, cmd, channel, access_level, description, help, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                self.db.exec(sql, [module, handler, command, channel, access_level, description, help_topic, default_status])
