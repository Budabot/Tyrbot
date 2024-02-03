from core.buddy_service import BuddyService
from core.chat_blob import ChatBlob
from core.command_param_types import Character, Const, Options, Any
from core.db import DB
from core.decorators import instance, command
from core.lookup.pork_service import PorkService
from core.sender_obj import SenderObj
from core.standard_message import StandardMessage
from core.text import Text
from core.tyrbot import Tyrbot
import time

@instance()
class KosListController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.bot: Tyrbot = registry.get_instance("bot")
        self.buddy_service: BuddyService = registry.get_instance("buddy_service")
        self.db: DB = registry.get_instance("db")
        self.pork_service: PorkService = registry.get_instance("pork_service")
        self.text: Text = registry.get_instance("text")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS kos_list (target_id INT PRIMARY KEY, submitter_id INT NOT NULL,"
                     " submitted_at INT NOT NULL, reason VARCHAR(2000) NOT NULL DEFAULT '')")

    @command(command="kos", params=[], access_level="member", description="Shows the kill-on-sight list")
    def kos_list_show_cmd2(self, request):
        entries = self.db.query("SELECT p1.char_id AS char_id, p1.name AS name, p1.level AS level, p1.ai_level AS ai_level, p1.profession AS profession, p1.faction AS faction, "
                                "p1.org_name AS org_name, p1.org_rank_name AS org_rank_name, "
                                "p2.name AS kos_submitter_name, kos_list.reason AS kos_reason, kos_list.submitted_at AS kos_submitted_at "
                                "FROM kos_list "
                                "LEFT JOIN player p1 ON kos_list.target_id = p1.char_id "
                                "LEFT JOIN player p2 ON kos_list.submitter_id = p2.char_id "
                                "ORDER BY p1.name ASC")
        count = len(entries)
        
        if count == 0:
            return "The kill-on-sight list is empty."
        
        blob = ""
        for entry in entries:
            blob += self.text.format_char_info(entry, self.buddy_service.is_online(entry.char_id))
            if (len(entry.kos_reason) == 0):
                blob += " (by %s)" % entry.kos_submitter_name
            else:
                blob += " (by %s: %s)" % (entry.kos_submitter_name, entry.kos_reason)
            blob += "\n"
        
        return ChatBlob("Kill-on-sight List (%d)" % count, blob)
        
    @command(command="kos", params=[Const("add"), Character("character"), Any("reason", is_optional=True)], access_level="member",
             description="Adds a character to the kill-on-sight list")
    def kos_list_add_cmd(self, request, _, target: SenderObj, reason):
        if not target.char_id:
            return StandardMessage.char_not_found(target.name)
        
        sql = "INSERT INTO kos_list (target_id, submitter_id, submitted_at, reason) VALUES (?,?,?,?) ON CONFLICT (target_id) DO NOTHING"
        result = self.db.exec(sql, [target.char_id, request.sender.char_id, int(time.time()), str(reason or "")])
        if result == 0:
            return "Character <highlight>%s</highlight> is already on the kill-on-sight list." % target.name
        
        # send the reply and afterwards trigger an info fetch from PoRK to update the database
        # the reply needs to be sent first to avoid the unnecessary delay from the PoRK request
        request.reply("Character <highlight>%s</highlight> has been added to the kill-on-sight list." % target.name)
        self.pork_service.get_character_info(target.name)
    
    @command(command="kos", params=[Options(["rem", "remove"]), Character("character")], sub_command="remove", access_level="moderator",
             description="Removes a character from the kill-on-sight list")
    def kos_list_remove_cmd(self, request, _, target: SenderObj):
        if not target.char_id:
            return StandardMessage.char_not_found(target.name)
        
        result = self.db.exec("DELETE FROM kos_list WHERE target_id = ?", [target.char_id])
        if result == 0:
            return "Character <highlight>%s</highlight> is not on the kill-on-sight list." % target.name
        
        return "Character <highlight>%s</highlight> has been removed from the kill-on-sight list." % target.name