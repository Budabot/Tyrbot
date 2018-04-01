from core.decorators import instance, command, event
from core.commands.param_types import Any, Const, Options
from core.chat_blob import ChatBlob
from core.buddy_manager import BuddyManager
import os


@instance()
class MemberController:
    BUDDY_TYPE = "member"

    def __init__(self):
        pass

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.character_manager = registry.get_instance("character_manager")
        self.private_channel_manager = registry.get_instance("private_channel_manager")
        self.buddy_manager = registry.get_instance("buddy_manager")
        self.bot = registry.get_instance("budabot")

    def start(self):
        self.db.load_sql_file("members.sql", os.path.dirname(__file__))
        # TODO register access_level
        # TODO add !autoinivte command

    @command(command="member", params=[Const("add"), Any("character")], access_level="superadmin",
             description="Add a member")
    def member_add_cmd(self, channel, sender, reply, args):
        char = args[1].lower().capitalize()
        char_id = self.character_manager.resolve_char_to_id(char)
        if char_id:
            if self.get_member(char_id):
                reply("<highlight>%s<end> is already a member." % char)
            else:
                self.add_member(char_id)
                reply("<highlight>%s<end> has been added as a member." % char)
        else:
            reply("Could not find character <highlight>%s<end>." % char)

    @command(command="member", params=[Options(["rem", "remove"]), Any("character")], access_level="superadmin",
             description="Remove a member")
    def member_remove_cmd(self, channel, sender, reply, args):
        char = args[2].lower().capitalize()
        char_id = self.character_manager.resolve_char_to_id(char)
        if char_id:
            if self.get_member(char_id):
                self.remove_member(char_id)
                reply("<highlight>%s<end> has been removed as a member." % char)
            else:
                reply("<highlight>%s<end> is not a member." % char)
        else:
            reply("Could not find character <highlight>%s<end>." % char)

    @command(command="member", params=[Const("list")], access_level="superadmin",
             description="List members")
    def member_list_cmd(self, channel, sender, reply, args):
        data = self.get_all_members()
        count = len(data)
        blob = ""
        for row in data:
            blob += str(row.char_id) + "\n"
        reply(ChatBlob("Members (%d)" % count, blob))

    @event(event_type=BuddyManager.BUDDY_LOGON_EVENT, description="")
    def handle_buddy_logon(self, event_type, event_data):
        member = self.get_member(event_data.character_id)
        if member and member.auto_invite == 1:
            self.bot.send_private_message(member.char_id, "You have been auto-invited to the private channel.")
            self.private_channel_manager.invite(member.char_id)

    def add_member(self, char_id, auto_invite=1):
        self.buddy_manager.add_buddy(char_id, self.BUDDY_TYPE)
        self.db.exec("INSERT INTO members (char_id, auto_invite) VALUES (?, ?)", [char_id, auto_invite])

    def remove_member(self, char_id):
        self.buddy_manager.remove_buddy(char_id, self.BUDDY_TYPE)
        self.db.exec("DELETE FROM members WHERE char_id = ?", [char_id])

    def update_auto_invite(self, char_id, auto_invite):
        self.db.exec("UPDATE members SET auto_invite = ? WHERE char_id = ?", [auto_invite, char_id])

    def get_member(self, char_id):
        return self.db.query_single("SELECT char_id, auto_invite FROM members WHERE char_id = ?", [char_id])

    def get_all_members(self):
        return self.db.query("SELECT char_id, auto_invite FROM members")
