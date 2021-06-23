from core.db import DB
from core.command_param_types import Const
from core.decorators import instance, command
from core.dict_object import DictObject
from core.logger import Logger


@instance()
class MigrateController:
    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.character_service = registry.get_instance("character_service")
        self.alts_service = registry.get_instance("alts_service")
        self.pork_service = registry.get_instance("pork_service")

    def pre_start(self):
        self.bot_name = "bot_name"
        database = DictObject({"type": "mysql",
                               "name": "database_name",
                               "username": "username",
                               "password": "password",
                               "host": "localhost",
                               "port": 3306})

        self.db2 = DB()
        self.db2.connect_mysql(database.host, database.port, database.username, database.password, database.name)

    @command(command="bebot", params=[Const("migrate"), Const("alts")], access_level="superadmin",
             description="Migrate alts from a Bebot database")
    def migrate_alts_cmd(self, request, _1, _2):
        data = self.db2.query("SELECT a.alt, u1.char_id AS alt_char_id, a.main, u2.char_id AS main_char_id "
                              "FROM alts a "
                              f"LEFT JOIN {self.bot_name}_users u1 ON a.alt = u1.nickname "
                              f"LEFT JOIN {self.bot_name}_users u2 ON a.main = u2.nickname "
                              "WHERE a.confirmed = 1 "
                              "ORDER BY main, alt")
        current_main = None
        current_main_id = None
        count_inactive = 0
        count_success = 0
        count_failure = 0

        request.reply("Processing %s alt records..." % len(data))

        for row in data:
            if row.main != current_main:
                current_main = row.main
                current_main_id = self.resolve_to_char_id(row.main, row.main_char_id)

            if not current_main_id:
                self.logger.warning(f"Could not resolve main char '{current_main}' to char id")
                count_inactive += 1
                continue

            alt_id = self.resolve_to_char_id(row.alt, row.alt_char_id)
            if not alt_id:
                self.logger.warning(f"Could not resolve alt char '{row.alt}' to char id")
                count_inactive += 1
                continue

            msg, result = self.alts_service.add_alt(current_main_id, alt_id)
            if result:
                count_success += 1
            else:
                count_failure += 1

        return f"<highlight>{count_success}</highlight> alts were migrated successfully, " \
               f"<highlight>{count_failure}</highlight> alts failed to be added, " \
               f"and <highlight>{count_inactive}</highlight> chars were inactive and could not be resolved to char ids."

    @command(command="bebot", params=[Const("migrate"), Const("logon")], access_level="superadmin",
             description="Migrate logon messages from a Bebot database")
    def migrate_logon_cmd(self, request, _1, _2):
        data = self.db2.query(f"SELECT message, id FROM {self.bot_name}_logon")

        request.reply("Processing %s logon records..." % len(data))

        for row in data:
            self.db.exec("INSERT INTO log_messages (char_id, logon) VALUES(?, ?)", [row.id, row.message])

        return f"Logon messages migrated successfully."

    @command(command="budabot", params=[Const("migrate"), Const("quotes")], access_level="superadmin",
             description="Migrate quotes from a Bebot database")
    def migrate_quotes_cmd(self, request, _1, _2):
        data = self.db2.query("SELECT p.charid AS char_id, q.id, q.msg, q.dt FROM quote q LEFT JOIN players p ON q.poster = p.name")
        count_inactive = 0

        request.reply("Processing %s quote records..." % len(data))

        for row in data:
            char_id = self.resolve_to_char_id(row.poster, row.char_id)

            if not char_id:
                char_id = -1
                count_inactive += 1

            self.db.exec("INSERT INTO quote (id, char_id, created_at, content) VALUES (?, ?, ?, ?)", [row.id, char_id, row.dt, row.msg])

        return f"Quotes successfully migrated. <highlight>{count_inactive}</highlight> posters were inactive and could not be resolved to char ids."

    @command(command="budabot", params=[Const("migrate"), Const("log_messages")], access_level="superadmin",
             description="Migrate quotes from a Bebot database")
    def migrate_log_messages_cmd(self, request, _1, _2):
        data = self.db2.query("SELECT p2.charid AS char_id, p1.sender, p1.name, p1.value FROM preferences_<myname> p1 LEFT JOIN players p2 ON p1.sender = p2.name "
                              "WHERE p1.name = 'logon_msg' OR p1.name = 'logoff_msg'")
        count_inactive = 0

        request.reply("Processing %s log messages records..." % len(data))

        for row in data:
            char_id = self.resolve_to_char_id(row.sender, row.char_id)

            if not char_id:
                count_inactive += 1
            else:
                existing = self.db.query_single("SELECT 1 FROM log_messages WHERE char_id = ?", [char_id])

                if not existing:
                    self.db.exec("INSERT INTO log_messages (char_id, logon, logoff) VALUES (?, NULL, NULL)", [char_id])

                if row.value == 'logon_msg':
                    self.db.exec("UPDATE log_messages SET logon = ? WHERE char_id = ?", [char_id, row.value])
                elif row.value == 'logoff_msg':
                    self.db.exec("UPDATE log_messages SET logoff = ? WHERE char_id = ?", [char_id, row.value])

        return f"<highlight>{len(data)}</highlight> logon and logoff messages successfully migrated. <highlight>{count_inactive}</highlight> messages were from inactive characters that could not be resolved to char ids."

    def resolve_to_char_id(self, name, char_id):
        if char_id and char_id > 0:
            return char_id

        char_id = self.character_service.resolve_char_to_id(name)
        if char_id:
            return char_id

        char_info = self.pork_service.get_character_info(name)
        if char_info:
            return char_info.char_id

        return None
