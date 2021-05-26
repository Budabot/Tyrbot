import time

from core.admin_service import AdminService
from core.chat_blob import ChatBlob
from core.command_param_types import Const, Character, Options, Any
from core.db import DB
from core.decorators import instance, command
from core.translation_service import TranslationService


@instance()
class BroadcastController:
    MESSAGE_SOURCE = "broadcast"

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.character_service = registry.get_instance("character_service")
        self.command_service = registry.get_instance("command_service")
        self.message_hub_service = registry.get_instance("message_hub_service")
        self.ts: TranslationService = registry.get_instance("translation_service")
        self.access_service = registry.get_instance("access_service")
        self.getresp = self.ts.get_response

    def pre_start(self):
        self.message_hub_service.register_message_source(self.MESSAGE_SOURCE)

    def start(self):
        self.command_service.register_command_pre_processor(self.command_pre_process)
        self.db.exec("CREATE TABLE IF NOT EXISTS broadcast (char_id INT NOT NULL PRIMARY KEY, alias VARCHAR(50), created_at INT NOT NULL)")

    @command(command="broadcast", params=[], access_level="admin",
             description="Show characters/bots on the broadcast list")
    def broadcast_list_cmd(self, request):
        data = self.db.query("SELECT p.name, alias FROM broadcast b JOIN player p ON b.char_id = p.char_id ORDER BY p.name ASC")

        blob = ""
        for row in data:
            blob += row.name
            if row.alias:
                blob += " (" + row.alias + ")"
            blob += "\n"

        return ChatBlob("Broadcast List (%d)" % len(data), blob)

    @command(command="broadcast", params=[Const("add"), Character("char"), Any("alias", is_optional=True)], access_level="admin",
             description="Add a character/bot to the broadcast list")
    def broadcast_add_cmd(self, request, _, char, alias):
        if char.char_id is None:
            return self.getresp("global", "char_not_found", {"char": char.name})

        if char.char_id == request.sender.char_id:
            return "You cannot add yourself to the broadcast list."

        if self.access_service.check_access(char.char_id, AdminService.MODERATOR):
            return "You cannot add a moderator or admin to the broadcast list."

        row = self.db.query_single("SELECT 1 FROM broadcast WHERE char_id = ?", [char.char_id])

        if row:
            return f"Error! <highlight>{char.name}</highlight> already exists on the broadcast list."
        else:
            self.db.exec("INSERT INTO broadcast (char_id, alias, created_at) VALUES (?, ?, ?)", [char.char_id, alias, int(time.time())])
            return f"<highlight>{char.name}</highlight> has been added to the broadcast list."

    @command(command="broadcast", params=[Options(["rem", "remove"]), Character("char")], access_level="admin",
             description="Remove a character/bot from the broadcast list")
    def broadcast_remove_cmd(self, request, _, char):
        if char.char_id is None:
            return self.getresp("global", "char_not_found", {"char": char.name})

        row = self.db.query_single("SELECT 1 FROM broadcast WHERE char_id = ?", [char.char_id])

        if not row:
            return f"Error! <highlight>{char.name}</highlight> does not exist on the broadcast list."
        else:
            self.db.exec("DELETE FROM broadcast WHERE char_id = ?", [char.char_id])
            return f"<highlight>{char.name}</highlight> has been removed from the broadcast list."

    def command_pre_process(self, context):
        row = self.db.query_single("SELECT alias FROM broadcast WHERE char_id = ?", [context.char_id])
        if row:
            if row.alias:
                name = row.alias
            else:
                name = self.character_service.resolve_char_to_name(context.char_id)
            formatted_message = "[%s] %s" % (name, context.message)
            self.message_hub_service.send_message(self.MESSAGE_SOURCE, None, None, formatted_message)
            return False
        else:
            return True
