import hjson

from core.decorators import instance, command
from core.command_param_types import Any, Const, Options, Time, Character
from core.chat_blob import ChatBlob
import time

from core.translation_service import TranslationService


@instance()
class BanController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.ban_service = registry.get_instance("ban_service")
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.ts: TranslationService = registry.get_instance("translation_service")
        self.getresp = self.ts.get_response

    def start(self):
        self.command_alias_service.add_alias("unban", "ban rem")
        self.ts.register_translation("module/ban", self.load_ban_msg)

    def load_ban_msg(self):
        with open("modules/core/ban/ban.msg", mode="r", encoding="UTF-8") as f:
            return hjson.load(f)

    @command(command="ban", params=[Const("list", is_optional=True)], access_level="moderator",
             description="Show the ban list")
    def ban_list_cmd(self, request, _):
        t = int(time.time())
        data = self.ban_service.get_ban_list()
        blob = ""
        for row in data:
            ends = "never" if row.finished_at == -1 else self.util.format_datetime(row.finished_at)
            time_left = "" if row.finished_at == -1 else " (%s left)" % self.util.time_to_readable(row.finished_at - t)
            blob += self.getresp("module/ban", "list_blob", {"char": row.name,
                                                             "added_time": self.util.format_datetime(row.created_at),
                                                             "banner": row.sender_name,
                                                             "end_time": ends,
                                                             "left": time_left,
                                                             "reason": row.reason})
        return ChatBlob(self.getresp("module/ban", "list", {"amount": len(data)}), blob)

    @command(command="ban", params=[Options(["rem", "remove"]), Character("character")], access_level="moderator",
             description="Remove a character from the ban list")
    def ban_remove_cmd(self, request, _, char):
        if not char.char_id:
            return self.getresp("global", "char_not_found", {"char": char.name})
        elif not self.ban_service.get_ban(char.char_id):
            return self.getresp("module/ban", "not_banned", {"char": char.name})
        else:
            self.bot.send_private_message(char.char_id, self.getresp("module/ban", "unbanned_target",
                                                                     {"char": request.sender.name}))
            self.ban_service.remove_ban(char.char_id)
            return self.getresp("module/ban", "unbanned_self", {"char": char.name})

    @command(command="ban",
             params=[Const("add", is_optional=True), Character("character"), Time("duration", is_optional=True),
                     Any("reason", is_optional=True)], access_level="moderator",
             description="Add a character to the ban list")
    def ban_add_cmd(self, request, _, char, duration, reason):
        if not char.char_id:
            return self.getresp("global", "char_not_found", {"char": char.name})
        elif self.ban_service.get_ban(char.char_id):
            return self.getresp("module/ban", "already_banned", {"char":char.name})
        else:
            duration_str = self.util.time_to_readable(duration) if duration else "permanent"
            if reason:
                msg = self.getresp("module/ban", "banned_target_1", {"banner": request.sender.name,
                                                                     "reason": reason, "duration":
                                                                         duration_str})
            else:
                msg = self.getresp("module/ban", "banned_target_2", {"banner": request.sender.name,
                                                                     "duration": duration_str})
            self.bot.send_private_message(char.char_id, msg)
            self.ban_service.add_ban(char.char_id, request.sender.char_id, duration, reason)
            return self.getresp("module/ban", "banned_self", {"char":char.name})
