from core.decorators import instance, command
from core.command_param_types import Any, Const, Options, Time, Character, NamedFlagParameters
from core.chat_blob import ChatBlob
import time

from core.standard_message import StandardMessage


@instance()
class BanController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.ban_service = registry.get_instance("ban_service")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("unban", "ban rem")

    @command(command="ban", params=[Const("list", is_optional=True), NamedFlagParameters(["include_expired"])], access_level="moderator",
             description="Show the ban list")
    def ban_list_cmd(self, request, _, flag_params):
        t = int(time.time())
        data = self.ban_service.get_ban_list(flag_params.include_expired)
        blob = ""
        for row in data:
            end_time = "never" if row.finished_at == -1 else self.util.format_datetime(row.finished_at)
            time_left = "" if row.finished_at == -1 else " (%s left)" % self.util.time_to_readable(row.finished_at - t)
            added_time = self.util.format_datetime(row.created_at)
            name = row.name if row.name else ("Unknown(%d)" % row.char_id)

            blob += f"<pagebreak>Name: <highlight>{name}</highlight>\n"
            blob += f"Added: <highlight>{added_time}</highlight>\n"
            blob += f"By: <highlight>{row.sender_name}</highlight>\n"
            blob += f"Ends: <highlight>{end_time}</highlight>{time_left}\n"
            blob += f"Reason: <highlight>{row.reason}</highlight>\n\n"

        return ChatBlob(f"Ban List ({len(data)})", blob)

    @command(command="ban", params=[Options(["rem", "remove"]), Character("character")], access_level="moderator",
             description="Remove a character from the ban list")
    def ban_remove_cmd(self, request, _, char):
        if not char.char_id:
            return StandardMessage.char_not_found(char.name)

        if not self.ban_service.get_ban(char.char_id):
            return f"<highlight>{char.name}</highlight> is not banned."

        self.ban_service.remove_ban(char.char_id)
        return f"<highlight>{char.name}</highlight> has been removed from the ban list."

    @command(command="ban",
             params=[Const("add", is_optional=True), Character("character"), Time("duration", is_optional=True),
                     Any("reason", is_optional=True)],
             access_level="moderator", description="Add a character to the ban list")
    def ban_add_cmd(self, request, _, char, duration, reason):
        if not char.char_id:
            return StandardMessage.char_not_found(char.name)

        if self.ban_service.get_ban(char.char_id):
            return f"<highlight>{char.name}</highlight> is already banned."

        if reason and len(reason) > 255:
            return "Ban reason cannot be more than 255 characters."

        self.ban_service.add_ban(char.char_id, request.sender.char_id, duration, reason)
        return f"<highlight>{char.name}</highlight> has been added to the ban list."
