from core.chat_blob import ChatBlob
from core.command_param_types import Character, Const, Options, Any
from core.decorators import instance, command
from core.sender_obj import SenderObj
from core.standard_message import StandardMessage
import time

@instance()
class KosListController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.buddy_service = registry.get_instance("buddy_service")
        self.db = registry.get_instance("db")
        self.pork_service = registry.get_instance("pork_service")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS kos_list (target_id INT PRIMARY KEY, submitter_id INT NOT NULL,"
                     " submitted_at INT NOT NULL, reason VARCHAR(2000) NOT NULL DEFAULT '')")
    
    @command(command="kos", params=[], access_level="member", description="Shows the kill-on-sight list")
    def kos_list_show_cmd(self, request):
        entries = self.db.query("SELECT kos_list.target_id AS target_id, p1.name AS target_name, "
                                "p2.name AS submitter_name, kos_list.submitted_at AS submitted_at, kos_list.reason AS reason "
                                "FROM kos_list "
                                "LEFT JOIN player p1 ON kos_list.target_id = p1.char_id "
                                "LEFT JOIN player p2 ON kos_list.submitter_id = p2.char_id "
                                "ORDER BY kos_list.submitted_at DESC")
        count = len(entries)
        
        if count == 0:
            return "The kill-on-sight list is empty"
        
        blob = ""
        for entry in entries:
            target_info = self.pork_service.get_character_info(entry.target_name)
            blob += "<highlight>%s</highlight> " % entry.target_name
            if target_info is not None:
                blob += "%s (%d/<green>%d</green>) " % (target_info.profession, target_info.level, target_info.ai_level)
            if self.buddy_service.is_online(entry.target_id):
                blob += "<green>online</green> "
            if (len(entry.reason) == 0):
                blob += "added by %s" % entry.submitter_name
            else:
                blob += "added by %s: %s" % (entry.submitter_name, entry.reason)
            blob += "\n"
        
        return ChatBlob("Kill-on-sight list (%d)" % count, blob)
        
    @command(command="kos", params=[Const("add"), Character("character"), Any("reason", is_optional=True)], access_level="member",
             description="Adds a character to the kill-on-sight list")
    def kos_list_add_cmd(self, request, _, target: SenderObj, reason):
        if not target.char_id:
            return StandardMessage.char_not_found(target.name)
        
        sql = "INSERT INTO kos_list (target_id, submitter_id, submitted_at, reason) VALUES (?,?,?,?) ON CONFLICT (target_id) DO NOTHING"
        result = self.db.exec(sql, [target.char_id, request.sender.char_id, int(time.time()), str(reason or "")])
        if result == 0:
            return "Character <highlight>%s</highlight> is already on the kill-on-sight list." % target.name
        
        return "Character <highlight>%s</highlight> has been added to the kill-on-sight list." % target.name
    
    @command(command="kos", params=[Options(["rem", "remove"]), Character("character")], sub_command="remove", access_level="moderator",
             description="Removes a character from the kill-on-sight list")
    def kos_list_remove_cmd(self, request, _, target: SenderObj):
        if not target.char_id:
            return StandardMessage.char_not_found(target.name)
        
        result = self.db.exec("DELETE FROM kos_list WHERE target_id = ?", [target.char_id])
        if result == 0:
            return "Character <highlight>%s</highlight> is not on the kill-on-sight list." % target.name
        
        return "Character <highlight>%s</highlight> has been removed from the kill-on-sight list." % target.name