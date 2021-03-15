from core.command_param_types import Const
from core.decorators import instance, command
from core.dict_object import DictObject
from core.logger import Logger


@instance()
class MigrateController:
    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        # self.db = registry.get_instance("db")
        self.character_service = registry.get_instance("character_service")
        self.alts_service = registry.get_instance("alts_service")

    def pre_start(self):
        database = DictObject({"type": "mysql",
                               "name": "my-database",
                               "username": "username",
                               "password": "password",
                               "host": "localhost",
                               "port": 3306})

        self.db2.connect_mysql(database.host, database.port, database.username, database.password, database.name)

    @command(command="bebot", params=[Const("migrate"), Const("alts")], access_level="superadmin",
             description="Migrate alts from a Bebot database")
    def migrate_alts_cmd(self, request, _1, _2):
        data = self.db2.query("SELECT alt, main FROM alts WHERE confirmed = 1 ORDER BY main, alt")
        current_main = None
        current_main_id = None
        count_inactive = 0
        count_success = 0
        count_failure = 0

        request.reply("Processing %s alt records..." % len(data))

        for row in data:
            if row.main != current_main:
                current_main = row.main
                current_main_id = self.character_service.resolve_char_to_id(current_main)

            if not current_main_id:
                self.logger.warning(f"Could not resolve main char '{current_main}' to char id")
                count_inactive += 1
                continue

            alt_id = self.character_service.resolve_char_to_id(row.alt)
            if not current_main_id:
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

    @command(command="budabot", params=[Const("migrate"), Const("quotes")], access_level="superadmin",
             description="Migrate quotes from a Bebot database")
    def migrate_quotes_cmd(self, request, _1, _2):
        data = self.db2.query("SELECT p.charid AS char_id, q.id, q.msg, q.dt FROM quote q LEFT JOIN players p ON q.poster = p.name")
        count_inactive = 0

        request.reply("Processing %s quote records..." % len(data))

        for row in data:
            if row.char_id:
                char_id = row.char_id
            else:
                char_id = self.character_service.resolve_char_to_id(row.poster)

            if not char_id:
                char_id = -1
                count_inactive += 1

            self.db.exec("INSERT INTO quote (id, char_id, created_at, content) VALUES (?, ?, ?)", [row.id, char_id, row.dt, row.msg])

        return f"Quotes successfully migrated. <highlight>{count_inactive}</highlight> posters were inactive and could not be resolved to char ids."
