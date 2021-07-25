from core.alts_service import AltsService
from core.db import DB
from core.command_param_types import Const
from core.decorators import instance, command
from core.dict_object import DictObject
from core.logger import Logger


@instance()
class MigrateController:
    DATABASE_TYPE_MYSQL = "mysql"
    DATABASE_TYPE_SQLITE = "sqlite"

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.character_service = registry.get_instance("character_service")
        self.alts_service = registry.get_instance("alts_service")
        self.pork_service = registry.get_instance("pork_service")

    def pre_start(self):
        self.db2 = DB()

        # REQUIRED: the name of the bot character that the budabot/bebot ran as
        self.bot_name = "bot_name"

        # if your budabot/bebot used mysql, then uncomment the second line below and fill out the appropriate values
        # otherwise, if your budabot used sqlite, then uncomment the first line below and enter the path to the sqlite db file
        # do NOT uncomment both of them
        # REQUIRED: uncomment ONE of these two lines below

        # self.db2.connect_sqlite("./data/budabot.db")
        # self.db2.connect_mysql(host="localhost", port=3306, username="", password="", database_name="")

    @command(command="bebot", params=[Const("migrate"), Const("alts")], access_level="superadmin",
             description="Migrate alts from a Bebot database")
    def migrate_bebot_alts_cmd(self, request, _1, _2):
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
    def migrate_bebot_logon_cmd(self, request, _1, _2):
        data = self.db2.query(f"SELECT message, id FROM {self.bot_name}_logon")

        request.reply("Processing %s logon records..." % len(data))

        for row in data:
            self.db.exec("INSERT INTO log_messages (char_id, logon) VALUES(?, ?)", [row.id, row.message])

        return f"Successfully migrated <highlight>%d</highlight> logon messages." % len(data)

    @command(command="budabot", params=[Const("migrate"), Const("admins")], access_level="superadmin",
             description="Migrate admins from a Budabot database")
    def migrate_budabot_admins_cmd(self, request, _1, _2):
        data = self.db2.query("SELECT a.name, p.charid AS char_id, CASE WHEN adminlevel = 4 THEN 'admin' WHEN adminlevel = 3 THEN 'moderator' END AS access_level "
                              "FROM admin_<myname> a LEFT JOIN players p ON a.name = p.name WHERE p.charid > 0")
        with self.db.transaction():
            for row in data:
                char_id = self.resolve_to_char_id(row.name, row.char_id)

                if char_id:
                    self.db.exec("DELETE FROM admin WHERE char_id = ?", [char_id])
                    self.db.exec("INSERT INTO admin (char_id, access_level) VALUES (?, ?)", [char_id, row.access_level])
                else:
                    # TODO
                    pass

        return f"Successfully migrated <highlight>%d</highlight> admin characters." % len(data)

    @command(command="budabot", params=[Const("migrate"), Const("banlist")], access_level="superadmin",
             description="Migrate ban list from a Budabot database")
    def migrate_budabot_banlist_cmd(self, request, _1, _2):
        data = self.db2.query("SELECT b.charid AS char_id, p.charid AS sender_char_id, time AS created_at, banend AS finished_at, reason "
                              "FROM banlist_<myname> b JOIN players p ON b.admin = p.name WHERE p.charid > 0")
        with self.db.transaction():
            for row in data:
                self.db.exec("DELETE FROM ban_list WHERE char_id = ?", [row.char_id])
                self.db.exec("INSERT INTO ban_list (char_id, sender_char_id, created_at, finished_at, reason, ended_early) VALUES (?, ?, ?, ?, ?, ?)",
                             [row.char_id, row.sender_char_id, row.created_at, row.finished_at, row.reason, 0])

        return f"Successfully migrated <highlight>%d</highlight> banned characters." % len(data)

    @command(command="budabot", params=[Const("migrate"), Const("alts")], access_level="superadmin",
             description="Migrate alts from a Budabot database")
    def migrate_budabot_alts_cmd(self, request, _1, _2):
        data = self.db2.query("SELECT p1.charid AS main_char_id, p2.charid AS alt_char_id "
                              "FROM alts a JOIN players p1 ON p1.name = a.main JOIN players p2 ON p2.name = a.alt "
                              "WHERE validated = 1 AND p1.charid > 0 AND p2.charid > 0 ORDER BY a.main ASC")
        with self.db.transaction():
            current_main = 0
            group_id = 0
            for row in data:
                if row.main_char_id != current_main:
                    current_main = row.main_char_id
                    group_id = self.db.query_single("SELECT (COALESCE(MAX(group_id), 0) + 1) AS next_group_id FROM alts").next_group_id
                    self.db.exec("DELETE FROM alts WHERE char_id = ?", [row.main_char_id])
                    self.db.exec("INSERT INTO alts (char_id, group_id, status) VALUES (?, ?, ?)", [row.main_char_id, group_id, AltsService.MAIN])

                self.db.exec("DELETE FROM alts WHERE char_id = ?", [row.alt_char_id])
                self.db.exec("INSERT INTO alts (char_id, group_id, status) VALUES (?, ?, ?)", [row.alt_char_id, group_id, AltsService.CONFIRMED])

        return f"Successfully migrated <highlight>%d</highlight> alt characters." % len(data)

    @command(command="budabot", params=[Const("migrate"), Const("members")], access_level="superadmin",
             description="Migrate members from a Budabot database")
    def migrate_budabot_members_cmd(self, request, _1, _2):
        data = self.db2.query("SELECT m.name AS sender, p.charid AS char_id, m.autoinv AS auto_invite FROM members_<myname> m JOIN players p ON m.name = p.name WHERE p.charid > 0")

        num = 0
        for row in data:
            char_id = self.resolve_to_char_id(row.sender, row.char_id)

            if char_id:
                num += 1
                self.db.exec("DELETE FROM member WHERE char_id = ?", [row.char_id])
                self.db.exec("INSERT INTO member (char_id, auto_invite) VALUES (?, ?)", [row.char_id, row.auto_invite])

        return f"Successfully migrated <highlight>{num}</highlight> members."

    @command(command="budabot", params=[Const("migrate"), Const("quotes")], access_level="superadmin",
             description="Migrate quotes from a Budabot database")
    def migrate_budabot_quotes_cmd(self, request, _1, _2):
        data = self.db2.query("SELECT q.poster, p.charid AS char_id, q.id, q.msg, q.dt FROM quote q LEFT JOIN players p ON q.poster = p.name")
        count_inactive = 0

        request.reply("Processing %s quote records..." % len(data))

        for row in data:
            char_id = self.resolve_to_char_id(row.poster, row.char_id)

            if not char_id:
                char_id = -1
                count_inactive += 1

            self.db.exec("DELETE FROM quote WHERE id = ?", [row.id])
            self.db.exec("INSERT INTO quote (id, char_id, created_at, content) VALUES (?, ?, ?, ?)", [row.id, char_id, row.dt, row.msg])

        return f"Quotes successfully migrated. <highlight>{count_inactive}</highlight> posters were inactive and could not be resolved to char ids."

    @command(command="budabot", params=[Const("migrate"), Const("log_messages")], access_level="superadmin",
             description="Migrate log messages from a Budabot database")
    def migrate_budabot_log_messages_cmd(self, request, _1, _2):
        data = self.db2.query(f"SELECT p2.charid AS char_id, p1.sender, p1.name, p1.value FROM preferences_{self.bot_name} p1 LEFT JOIN players p2 ON p1.sender = p2.name "
                              "WHERE p1.name = 'logon_msg' OR p1.name = 'logoff_msg'")
        count_inactive = 0
        count_logon = 0
        count_logoff = 0

        request.reply("Processing %s log messages records..." % len(data))

        for row in data:
            char_id = self.resolve_to_char_id(row.sender, row.char_id)

            if not char_id:
                count_inactive += 1
            else:
                existing = self.db.query_single("SELECT 1 FROM log_messages WHERE char_id = ?", [char_id])

                if not existing:
                    self.db.exec("INSERT INTO log_messages (char_id, logon, logoff) VALUES (?, NULL, NULL)", [char_id])

                if row.name == 'logon_msg' and row.value:
                    self.db.exec("UPDATE log_messages SET logon = ? WHERE char_id = ?", [row.value, char_id])
                    count_logon += 1
                elif row.name == 'logoff_msg' and row.value:
                    self.db.exec("UPDATE log_messages SET logoff = ? WHERE char_id = ?", [row.value, char_id])
                    count_logoff += 1

        return f"<highlight>{count_logon}</highlight> logon and <highlight>{count_logoff}</highlight> logoff messages successfully migrated. " \
               f"<highlight>{count_inactive}</highlight> messages were from inactive characters that could not be resolved to char ids."

    @command(command="budabot", params=[Const("migrate"), Const("name_history")], access_level="superadmin",
             description="Migrate name history from a Budabot database")
    def migrate_budabot_name_history_cmd(self, request, _1, _2):
        data = self.db2.query("SELECT charid AS char_id, name, dt AS created_at FROM name_history")

        request.reply("Processing %s name history records. This may take some time..." % len(data))

        for row in data:
            self.db.exec("DELETE FROM name_history WHERE char_id = ? AND name = ?", [row.char_id, row.name])
            self.db.exec("INSERT INTO name_history (char_id, name, created_at) VALUES (?, ?, ?)", [row.char_id, row.name, row.created_at])

        return f"Successfully migrated <highlight>%d</highlight> name history records." % len(data)

    @command(command="budabot", params=[Const("migrate"), Const("news")], access_level="superadmin",
             description="Migrate news from a Budabot database")
    def migrate_budabot_news_cmd(self, request, _1, _2):
        data = self.db2.query("SELECT n.name AS poster, p.charid AS char_id, news, sticky, time AS created_at, deleted AS deleted_at "
                              "FROM news n JOIN players p ON n.name = p.name WHERE p.charid > 0")
        for row in data:
            char_id = self.resolve_to_char_id(row.poster, row.char_id)

            if not char_id:
                char_id = -1

            self.db.exec("DELETE FROM news WHERE char_id = ? AND news = ?", [char_id, row.news])
            self.db.exec("INSERT INTO news (char_id, news, sticky, created_at, deleted_at) VALUES (?, ?, ?, ?, ?)", [char_id, row.news, row.sticky, row.created_at, row.deleted_at])

        return f"Successfully migrated <highlight>%d</highlight> news records." % len(data)

    @command(command="budabot", params=[Const("migrate"), Const("notes")], access_level="superadmin",
             description="Migrate notes from a Budabot database")
    def migrate_budabot_notes_cmd(self, request, _1, _2):
        data = self.db2.query("SELECT n.added_by AS sender, p.charid AS char_id, n.note, n.dt AS created_at "
                              "FROM notes n JOIN players p ON p.name = n.added_by WHERE p.charid > 0")

        num = 0
        for row in data:
            char_id = self.resolve_to_char_id(row.sender, row.char_id)

            if char_id:
                num += 1
                self.db2.exec("DELETE FROM notes WHERE char_id = ? AND note = ?", [char_id, row.note])
                self.db2.exec("INSERT INTO notes (char_id, note, created_at) VALUES (?, ?, ?)", [char_id, row.note, row.created_at])

        return f"Successfully migrated <highlight>{num}</highlight> note records."

    @command(command="budabot", params=[Const("migrate"), Const("last_seen")], access_level="superadmin",
             description="Migrate last_seen data from a Budabot database")
    def migrate_budabot_last_seen_cmd(self, request, _1, _2):
        data = self.db2.query("SELECT o.name AS sender, p.charid AS char_id, logged_off AS last_seen "
                              "FROM org_members_<myname> o JOIN players p ON o.name = p.name WHERE p.charid > 0")

        num = 0
        for row in data:
            char_id = self.resolve_to_char_id(row.sender, row.char_id)

            if char_id:
                num += 1
                self.db2.exec("DELETE FROM last_seen WHERE char_id = ?", [row.char_id])
                self.db2.exec("INSERT INTO last_seen (char_id, dt) VALUES (?, ?)", [row.char_id, row.last_seen])

        return f"Successfully migrated <highlight>{num}</highlight> last seen records."

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
