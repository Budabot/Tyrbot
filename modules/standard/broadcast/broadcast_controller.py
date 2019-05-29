import time

from core.chat_blob import ChatBlob
from core.command_param_types import Const, Character, Options
from core.db import DB
from core.decorators import instance, command


@instance()
class BroadcastController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.bot = registry.get_instance("bot")
        self.character_service = registry.get_instance("character_service")
        self.command_service = registry.get_instance("command_service")

    def start(self):
        self.command_service.register_command_pre_processor(self.command_pre_process)
        self.db.exec("CREATE TABLE IF NOT EXISTS broadcast (char_id INT NOT NULL PRIMARY KEY, created_at INT)")

    @command(command="broadcast", params=[], access_level="admin",
             description="Show characters/bots on the broadcast list")
    def broadcast_list_cmd(self, request):
        data = self.db.query("SELECT p.name FROM broadcast b JOIN player p ON b.char_id = p.char_id ORDER BY p.name ASC")

        blob = ""
        for row in data:
            blob += row.name + "\n"

        return ChatBlob("Broadcast List (%d)" % len(data), blob)

    @command(command="broadcast", params=[Const("add"), Character("char")], access_level="admin",
             description="Add a character/bot to the broadcast list")
    def broadcast_add_cmd(self, request, _, char):
        if char.char_id is None:
            return "Error! Could not find character <highlight>%s<end>." % char.name

        row = self.db.query_single("SELECT 1 FROM broadcast WHERE char_id = ?", [char.char_id])

        if row:
            return "Error! <highlight>%s<end> already exists on the broadcast list." % char.name
        else:
            self.db.exec("INSERT INTO broadcast (char_id, created_at) VALUES (?, ?)", [char.char_id, int(time.time())])
            return "<highlight>%s<end> has been added to the broadcast list." % char.name

    @command(command="broadcast", params=[Options(["rem", "remove"]), Character("char")], access_level="admin",
             description="Remove a character/bot from the broadcast list")
    def broadcast_remove_cmd(self, request, _, char):
        if char.char_id is None:
            return "Error! Could not find character <highlight>%s<end>." % char.name

        row = self.db.query_single("SELECT 1 FROM broadcast WHERE char_id = ?", [char.char_id])

        if not row:
            return "Error! <highlight>%s<end> does not exist on the broadcast list." % char.name
        else:
            self.db.exec("DELETE FROM broadcast WHERE char_id = ?", [char.char_id])
            return "<highlight>%s<end> has been removed from the broadcast list." % char.name

    def command_pre_process(self, context):
        row = self.db.query_single("SELECT 1 FROM broadcast WHERE char_id = ?", [context.char_id])
        if row:
            name = self.character_service.resolve_char_to_name(context.char_id)
            self.bot.send_org_message("[%s] %s" % (name, context.message), fire_outgoing_event=False)
            return False
        else:
            return True
