from core.decorators import instance, command, event
from core.command_param_types import Any, Const, Options
from core.chat_blob import ChatBlob
from core.buddy_service import BuddyService


@instance()
class MemberController:
    MEMBER_BUDDY_TYPE = "member"

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.character_service = registry.get_instance("character_service")
        self.private_channel_service = registry.get_instance("private_channel_service")
        self.buddy_service = registry.get_instance("buddy_service")
        self.bot = registry.get_instance("bot")
        self.access_service = registry.get_instance("access_service")

    def pre_start(self):
        self.access_service.register_access_level("member", 90, self.check_member)

    @event(event_type="connect", description="Add members as buddies of the bot on startup")
    def handle_connect_event(self, event_type, event_data):
        for row in self.get_all_members():
            if row.auto_invite == 1:
                self.buddy_service.add_buddy(row.char_id, self.MEMBER_BUDDY_TYPE)

    @command(command="member", params=[Const("add"), Any("character")], access_level="superadmin",
             description="Add a member")
    def member_add_cmd(self, request, _, char_name):
        char_name = char_name.capitalize()
        char_id = self.character_service.resolve_char_to_id(char_name)
        if char_id:
            if self.get_member(char_id):
                return "<highlight>%s<end> is already a member." % char_name
            else:
                self.add_member(char_id)
                return "<highlight>%s<end> has been added as a member." % char_name
        else:
            return "Could not find character <highlight>%s<end>." % char_name

    @command(command="member", params=[Options(["rem", "remove"]), Any("character")], access_level="superadmin",
             description="Remove a member")
    def member_remove_cmd(self, request, _, char_name):
        char_name = char_name.capitalize()
        char_id = self.character_service.resolve_char_to_id(char_name)
        if char_id:
            if self.get_member(char_id):
                self.remove_member(char_id)
                return "<highlight>%s<end> has been removed as a member." % char_name
            else:
                return "<highlight>%s<end> is not a member." % char_name
        else:
            return "Could not find character <highlight>%s<end>." % char_name

    @command(command="member", params=[Const("list")], access_level="superadmin",
             description="List members")
    def member_list_cmd(self, request, _):
        data = self.get_all_members()
        count = len(data)
        blob = ""
        for row in data:
            blob += str(row.char_id) + "\n"
        return ChatBlob("Members (%d)" % count, blob)

    @command(command="autoinvite", params=[Options(["on", "off"])], access_level="all",
             description="Set your auto invite preference")
    def autoinvite_cmd(self, request, pref):
        pref = pref.lower()
        member = self.get_member(request.sender.char_id)
        if member:
            self.update_auto_invite(request.sender.char_id, 1 if pref == "on" else 0)
            return "Your auto invite preference has been set to <highlight>%s<end>." % pref
        else:
            return "You must be a member of this bot to set your auto invite preference."

    @event(event_type=BuddyService.BUDDY_LOGON_EVENT, description="Auto invite members to the private channel when they logon")
    def handle_buddy_logon(self, event_type, event_data):
        member = self.get_member(event_data.char_id)
        if member and member.auto_invite == 1:
            self.bot.send_private_message(member.char_id, "You have been auto-invited to the private channel.")
            self.private_channel_service.invite(member.char_id)

    def add_member(self, char_id, auto_invite=1):
        self.buddy_service.add_buddy(char_id, self.MEMBER_BUDDY_TYPE)
        if not self.get_member(char_id):
            self.db.exec("INSERT INTO members (char_id, auto_invite) VALUES (?, ?)", [char_id, auto_invite])

    def remove_member(self, char_id):
        self.buddy_service.remove_buddy(char_id, self.MEMBER_BUDDY_TYPE)
        self.db.exec("DELETE FROM members WHERE char_id = ?", [char_id])

    def update_auto_invite(self, char_id, auto_invite):
        self.db.exec("UPDATE members SET auto_invite = ? WHERE char_id = ?", [auto_invite, char_id])

    def get_member(self, char_id):
        return self.db.query_single("SELECT char_id, auto_invite FROM members WHERE char_id = ?", [char_id])

    def get_all_members(self):
        return self.db.query("SELECT char_id, auto_invite FROM members")

    def check_member(self, char_id):
        return self.get_member(char_id) is not None
