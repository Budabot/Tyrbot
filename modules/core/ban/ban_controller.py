from core.decorators import instance, command
from core.command_param_types import Any, Const, Options, Time
from core.chat_blob import ChatBlob
import time


@instance()
class BanController:
    def inject(self, registry):
        self.text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.ban_service = registry.get_instance("ban_service")
        self.character_service = registry.get_instance("character_service")
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
            ends = "never" if row.finished_at == -1 else self.util.format_timestamp(row.finished_at)
            time_left = "" if row.finished_at == -1 else " (%s left)" % self.util.time_to_readable(row.finished_at - t)

            blob += "<pagebreak>Name: <highlight>%s<end>\n" % row.name
            blob += "Added: <highlight>%s<end>\n" % self.util.format_timestamp(row.created_at)
            blob += "By: <highlight>%s<end>\n" % row.sender_name
            blob += "Ends: <highlight>%s<end>%s\n" % (ends, time_left)
            blob += "Reason: <highlight>%s<end>\n\n" % row.reason

        return ChatBlob("Ban List (%d)" % len(data), blob)

    @command(command="ban", params=[Options(["rem", "remove"]), Any("character")], access_level="moderator",
             description="Remove a character from the ban list")
    def ban_remove_cmd(self, request, _, char_name):
        char_name = char_name.capitalize()
        char_id = self.character_service.resolve_char_to_id(char_name)

        if not char_id:
            return "Could not find <highlight>%s<end>." % char_name
        elif not self.ban_service.get_ban(char_id):
            return "<highlight>%s<end> is not banned." % char_name
        else:
            self.ban_service.remove_ban(char_id)
            return "<highlight>%s<end> has been removed from the ban list." % char_name

    @command(command="ban", params=[Const("add", is_optional=True), Any("character"), Time("duration", is_optional=True), Any("reason", is_optional=True)], access_level="moderator",
             description="Add a character to the ban list")
    def ban_add_cmd(self, request, _, char_name, duration, reason):
        char_name = char_name.capitalize()
        reason = reason or ""
        char_id = self.character_service.resolve_char_to_id(char_name)

        if not char_id:
            return "Could not find <highlight>%s<end>." % char_name
        elif self.ban_service.get_ban(char_id):
            return "<highlight>%s<end> is already banned." % char_name
        else:
            self.ban_service.add_ban(char_id, sender.char_id, duration, reason)
            return "<highlight>%s<end> has been added to the ban list." % char_name
