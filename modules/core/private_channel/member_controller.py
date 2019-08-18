from core.access_service import AccessService
from core.aochat.server_packets import BuddyAdded
from core.ban_service import BanService
from core.chat_blob import ChatBlob
from core.command_param_types import Const, Options, Character
from core.decorators import instance, command, event, setting
from core.setting_service import SettingService
from core.setting_types import TextSettingType, SettingType
from core.translation_service import TranslationService
from modules.core.org_members.org_member_controller import OrgMemberController


@instance()
class MemberController:
    MEMBER_ACCESS_LEVEL = "member"
    MEMBER_BUDDY_TYPE = "member"

    MEMBER_LOGON_EVENT = "member_logon_event"
    MEMBER_LOGOFF_EVENT = "member_logoff_event"

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.private_channel_service = registry.get_instance("private_channel_service")
        self.buddy_service = registry.get_instance("buddy_service")
        self.bot = registry.get_instance("bot")
        self.access_service: AccessService = registry.get_instance("access_service")
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.event_service = registry.get_instance("event_service")
        self.ts: TranslationService = registry.get_instance("translation_service")
        self.getresp = self.ts.get_response
        self.settings_service: SettingService = registry.get_instance("setting_service")
        self.org_member_controller: OrgMemberController = registry.get_instance("org_member_controller")

    def pre_start(self):
        self.access_service.register_access_level(self.MEMBER_ACCESS_LEVEL, 80, self.check_member)
        self.event_service.register_event_type(self.MEMBER_LOGON_EVENT)
        self.event_service.register_event_type(self.MEMBER_LOGOFF_EVENT)
        self.bot.add_packet_handler(BuddyAdded.id, self.handle_member_logon)

    def start(self):
        self.db.exec(
            "CREATE TABLE IF NOT EXISTS members (char_id INT NOT NULL PRIMARY KEY, auto_invite INT DEFAULT 0);")
        self.command_alias_service.add_alias("adduser", "member add")
        self.command_alias_service.add_alias("remuser", "member rem")
        self.command_alias_service.add_alias("members", "member")

    @setting(name="autoinvite_auto_al", value="org_member",
             description="Required Accesslevel to autoadd the player as an member (for the autoinvite)")
    def autoinvite_auto_al(self):
        return TextSettingType(["all", "guest", "member",
                                "org_member", "moderator",
                                "admin", "superadmin", "none"])

    @command(command="member", params=[Const("add"), Character("character")],
             access_level=OrgMemberController.ORG_ACCESS_LEVEL,
             description="Add a member")
    def member_add_cmd(self, request, _, char):
        if char.char_id:
            if self.get_member(char.char_id):
                return self.getresp("module/private_channel", "mem_add_fail", {"char": char.name})
            else:
                self.add_member(char.char_id)
                return self.getresp("module/private_channel", "mem_add_success", {"char": char.name})
        else:
            return self.getresp("global", "char_not_found", {"char": char.name})

    @command(command="member", params=[Options(["rem", "remove"]), Character("character")],
             access_level=OrgMemberController.ORG_ACCESS_LEVEL,
             description="Remove a member")
    def member_remove_cmd(self, request, _, char):
        if char.char_id:
            if self.get_member(char.char_id):
                self.remove_member(char.char_id)
                return self.getresp("module/private_channel", "mem_rem_success", {"char": char.name})
            else:
                return self.getresp("module/private_channel", "mem_rem_fail", {"char": char.name})
        else:
            return self.getresp("global", "char_not_found", {"char": char.name})

    @command(command="member", params=[Const("list", is_optional=True)],
             access_level=OrgMemberController.ORG_ACCESS_LEVEL,
             description="List members")
    def member_list_cmd(self, request, _):
        data = self.get_all_members()
        count = len(data)
        blob = ""
        for row in data:
            blob += str(row.name) + "\n"
        return ChatBlob(self.getresp("module/private_channel", "blob_mem_list", {"amount": count}), blob)

    @command(command="autoinvite", params=[Options(["on", "off"])], access_level=MEMBER_ACCESS_LEVEL,
             description="Set your auto invite preference")
    def autoinvite_cmd(self, request, pref):
        pref = pref.lower()
        member = self.get_member(request.sender.char_id)
        if member:
            self.update_auto_invite(request.sender.char_id, 1 if pref == "on" else 0)
            pref = self.getresp("module/private_channel", "on" if pref == "on" else "off")
            return self.getresp("module/private_channel", "autoinvite_changed", {"changedto": pref})
        else:
            if self.access_service.check_access(request.sender.char_id, self.settings_service.get_value("autoinvite_auto_al")):
                self.add_member(request.sender.char_id, auto_invite=1)
                return self.getresp("module/private_channel", "autoinvite_changed",
                                    {"changedto": self.getresp("module/private_channel", "on")})
            else:
                return self.getresp("module/private_channel", "not_an_member")

    @event(event_type="connect", description="Add members as buddies of the bot on startup", is_hidden=True)
    def handle_connect_event(self, event_type, event_data):
        for row in self.get_all_members():
            if row.auto_invite == 1:
                self.buddy_service.add_buddy(row.char_id, self.MEMBER_BUDDY_TYPE)

    @event(event_type=MEMBER_LOGON_EVENT, description="Auto invite members to the private channel when they logon")
    def handle_buddy_logon(self, event_type, event_data):
        if event_data.auto_invite == 1:
            self.bot.send_private_message(event_data.char_id, self.getresp("module/private_channel", "auto_invited"))
            self.private_channel_service.invite(event_data.char_id)

    @event(event_type=BanService.BAN_ADDED_EVENT, description="Remove characters as members when they are banned",
           is_hidden=True)
    def ban_added_event(self, event_type, event_data):
        self.remove_member(event_data.char_id)

    def handle_member_logon(self, packet: BuddyAdded):
        member = self.get_member(packet.char_id)
        if member:
            if packet.online:
                self.event_service.fire_event(self.MEMBER_LOGON_EVENT, member)
            else:
                self.event_service.fire_event(self.MEMBER_LOGOFF_EVENT, member)

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
        return self.db.query(
            "SELECT COALESCE(p.name, m.char_id) AS name, m.char_id, m.auto_invite FROM members m LEFT JOIN player p ON m.char_id = p.char_id ORDER BY p.name ASC")

    def check_member(self, char_id):
        return self.get_member(char_id) is not None
