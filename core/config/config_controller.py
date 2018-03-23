from core.decorators import instance, command, event, timerevent
from core.db import DB
from core.text import Text
from core.chat_blob import ChatBlob


@instance()
class ConfigController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.command_manager = registry.get_instance("command_manager")

    def start(self):
        pass

    @command(command="config", params="", access_level="superadmin", description="Shows configuration options for the bot")
    def config_list_cmd(self, command, channel, sender, reply, args):
        sql = """SELECT
                module,
                SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) count_enabled,
                SUM(CASE WHEN enabled = 0 THEN 1 ELSE 0 END) count_disabled
            FROM
                (SELECT module, enabled FROM command_config
                UNION
                SELECT module, enabled FROM event_config
                UNION
                SELECT module, 2 FROM setting) t
            GROUP BY
                module
            ORDER BY
                module ASC"""

        data = self.db.query(sql)
        count = len(data)
        blob = ""
        current_group = ""
        for row in data:
            parts = row.module.split(".")
            group = parts[0]
            if group != current_group:
                current_group = group
                blob += "\n<header2>" + current_group + "<end>\n"

            blob += self.text.make_chatcmd(row.module, "/tell <myname> config mod " + row.module) + " "
            if row.count_enabled > 0 and row.count_disabled > 0:
                blob += "<yellow>Partial<end>"
            elif row.count_disabled == 0:
                blob += "<green>Enabled<end>"
            else:
                blob += "<red>Disabled<end>"
            blob += "\n"
        reply(ChatBlob("Config (%d)" % count, blob))

    @command(command="config", params="mod (.+)", access_level="superadmin",
             description="Shows configuration options for the bot")
    def config_module_list_cmd(self, command, channel, sender, reply, args):
        module = args[1].lower()

        blob = ""

        data = self.db.query("SELECT name, description, value FROM setting WHERE module = ? ORDER BY name ASC", [module])
        if data:
            blob += "<header2>Settings<end>\n"
            for row in data:
                blob += row.description + ": " + row.value + "\n"

        data = self.db.query("SELECT DISTINCT command, sub_command FROM command_config WHERE module = ? ORDER BY command ASC",
                             [module])
        if data:
            blob += "\n<header2>Commands<end>\n"
            for row in data:
                blob += self.command_manager.get_command_key(row.command, row.sub_command) + "\n"

        data = self.db.query("SELECT event_type, handler, description FROM event_config WHERE module = ? "
                             "ORDER BY event_type, handler ASC",
                             [module])
        if data:
            blob += "\n<header2>Events<end>\n"
            for row in data:
                blob += row.event_type + " " + row.description + "\n"

        reply(ChatBlob(module + " Module Config", blob))
