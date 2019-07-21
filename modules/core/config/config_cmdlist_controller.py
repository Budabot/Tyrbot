from core.chat_blob import ChatBlob
from core.command_param_types import NamedParameters, Const
from core.db import DB
from core.decorators import instance, command
from core.text import Text
from core.translation_service import TranslationService


@instance()
class CommandListController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.command_service = registry.get_instance("command_service")
        self.ts: TranslationService = registry.get_instance("translation_service")
        self.getresp = self.ts.get_response

    @command(command="config", params=[Const("cmdlist"), NamedParameters(["access_level"])], access_level="admin",
             description="List all commands")
    def config_cmdlist_cmd(self, request, _, named_params):
        sql = "SELECT access_level, channel, enabled, command, module, sub_command FROM command_config"
        params = []
        if named_params.access_level:
            sql += " WHERE access_level = ?"
            params.append(named_params.access_level)
        sql += " ORDER BY module, command, sub_command, channel"
        data = self.db.query(sql, params)

        blob = ""
        current_module = ""
        current_command_key = ""
        count = 0
        temp_rows = []
        for row in data:
            if current_module != row.module:
                if temp_rows:
                    blob += self.display_row_data(temp_rows)
                    temp_rows = []
                blob += "\n<pagebreak><header2>%s<end>\n" % row.module
                current_module = row.module
                current_command_key = ""

            command_key = self.command_service.get_command_key(row.command, row.sub_command)
            if current_command_key != command_key:
                if temp_rows:
                    blob += self.display_row_data(temp_rows)
                    temp_rows = []
                count += 1
                blob += "%s - " % (self.text.make_chatcmd(command_key, "/tell <myname> config cmd " + command_key))
                current_command_key = command_key

            temp_rows.append(row)

        if temp_rows:
            blob += self.display_row_data(temp_rows)

        return ChatBlob(self.getresp("module/config", "cmdlist_commands", {"amount": count}), blob)

    def display_row_data(self, rows):
        return "[%s %s]\n" % (self.get_enabled_str(rows), self.get_access_levels_str(rows))

    def get_access_levels_str(self, rows):
        access_levels = list(map(lambda x: x.access_level, rows))
        if all(x == access_levels[0] for x in access_levels):
            return access_levels[0]
        else:
            return ",".join(access_levels)

    def get_enabled_str(self, rows):
        enabled = list(map(lambda x: x.enabled, rows))

        blob = ""
        if all(x == enabled[0] for x in enabled):
            blob += self.format_enabled(enabled[0])
        else:
            for x in enabled:
                blob += self.format_enabled(x)

        return blob

    def format_enabled(self, enabled):
        return "<green>E<end>" if enabled else "<red>D<end>"
