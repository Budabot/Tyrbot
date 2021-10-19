import time

from core.chat_blob import ChatBlob
from core.command_param_types import Time, Const, Any, NamedParameters
from core.decorators import instance, command
from core.logger import Logger
from core.standard_message import StandardMessage
from core.tyrbot import Tyrbot


@instance()
class UsageController:

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot: Tyrbot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.character_service = registry.get_instance("character_service")

    @command(command="usage", params=[Time("max_time", is_optional=True)], access_level="moderator",
             description="Show command usage summary")
    def usage_command(self, request, max_time):
        params = []
        sql = "SELECT command, count(1) AS count FROM command_usage "
        if max_time:
            sql += "WHERE created_at > ? "
            t = int(time.time())
            params.append(t - max_time)
        sql += "GROUP BY command ORDER BY count(1) DESC LIMIT 30"
        data = self.db.query(sql, params)

        rows = []
        for row in data:
            rows.append([f"<highlight>{row.count}</highlight>", row.command])

        display_table = self.text.pad_table(rows, " ", pad_right=False)

        blob = ""
        for cols in display_table:
            blob += "  ".join(cols) + "\n"

        if max_time:
            time_str = self.util.time_to_readable(max_time)
            title = f"Command Usage for {time_str}"
        else:
            title = "Command Usage"

        return ChatBlob(title, blob)

    @command(command="usage", params=[Const("history"), NamedParameters(["cmd", "char", "page"])], access_level="moderator",
             description="Show command usage history")
    def usage_history_command(self, request, _, named_params):
        page_size = 20
        page_number = int(named_params.page or "1")

        params = []
        sql = "SELECT channel, command, created_at, handler, p.name, c.char_id FROM command_usage c " \
              "LEFT JOIN player p ON c.char_id = p.char_id " \
              "WHERE 1=1"

        if named_params.cmd:
            sql += " AND (command LIKE ? OR handler LIKE ?)"
            params.append(named_params.cmd)
            params.append(named_params.cmd)

        if named_params.char:
            char_id = self.character_service.resolve_char_to_id(named_params.char)
            if not char_id:
                return StandardMessage.char_not_found(named_params.char)

            sql += " AND c.char_id = ?"
            params.append(char_id)

        sql += " ORDER BY created_at DESC LIMIT ?, ?"
        offset, limit = self.util.get_offset_limit(page_size, page_number)
        params.append(offset)
        params.append(limit)
        data = self.db.query(sql, params)

        rows = []
        for row in data:
            rows.append([row.command, row.channel, row.handler, (row.name or "Unknown(%s)" % row.char_id), self.util.format_datetime(row.created_at)])

        display_table = self.text.pad_table(rows, " ", pad_right=False)

        blob = ""
        cmd_string = "usage history"
        if named_params.cmd:
            cmd_string += f" --cmd={named_params.cmd}"
        if named_params.char:
            cmd_string += f" --char={named_params.char}"

        blob += self.text.get_paging_links(cmd_string, page_number, len(data) == page_size) + "\n\n"
        for cols in display_table:
            blob += "  ".join(cols) + "\n"

        title = "Command History"

        return ChatBlob(title, blob)
