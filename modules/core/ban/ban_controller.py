from core.decorators import instance, command
from core.command_param_types import Any, Const, Options, Time, Character
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

    @command(command="ban", params=[Const("list", is_optional=True)], access_level="moderator",
             description="Show the ban list")
    def ban_list_cmd(self, request, _):
        t = int(time.time())
        data = self.ban_service.get_ban_list()
        blob = ""
        for row in data:
            end_time = "never" if row.finished_at == -1 else self.util.format_datetime(row.finished_at)
            time_left = "" if row.finished_at == -1 else " (%s left)" % self.util.time_to_readable(row.finished_at - t)
            added_time = self.util.format_datetime(row.created_at)

            blob += f"<pagebreak>Name: <highlight>{row.name}</highlight>\n"
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

        self.bot.send_private_message(char.char_id,
                                      f"You have been unbanned by <highlight>{request.sender.name}</highlight>.",
                                      conn=request.conn)
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

        duration_str = self.util.time_to_readable(duration) if duration else "permanent"
        if reason:
            msg = f"You have been banned by <highlight>{request.sender.name}</highlight> for reason: <highlight>{reason}</highlight>. " \
                  f"Duration: <highlight>{duration_str}</highlight>."
        else:
            msg = f"You have been banned by <highlight>{request.sender.name}</highlight>. Duration: <highlight>{duration_str}</highlight>."

        self.bot.send_private_message(char.char_id, msg, conn=request.conn)
        self.ban_service.add_ban(char.char_id, request.sender.char_id, duration, reason)
        return f"<highlight>{char.name}</highlight> has been added to the ban list."
