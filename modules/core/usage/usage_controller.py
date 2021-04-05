import time

from core.chat_blob import ChatBlob
from core.command_param_types import Time
from core.decorators import instance, command
from core.logger import Logger
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

    @command(command="usage", params=[Time("max_time", is_optional=True)], access_level="moderator",
             description="Show command usage on the bot")
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
