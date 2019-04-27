from core.aochat.server_packets import BuddyAdded
from core.chat_blob import ChatBlob
from core.command_param_types import Const, Character
from core.decorators import instance, event, timerevent, command, setting
from core.logger import Logger
import time

from core.public_channel_service import PublicChannelService
from core.setting_types import NumberSettingType, TextSettingType
from modules.standard.org.org_activity_controller import OrgActivityController


@instance()
class OrgMemberController:
    ORG_BUDDY_TYPE = "org_member"
    ORG_ACCESS_LEVEL = "org_member"

    MODE_ADD_AUTO = "add_auto"
    MODE_REM_AUTO = "rem_auto"
    MODE_ADD_MANUAL = "add_manual"
    MODE_REM_MANUAL = "rem_manual"

    ORG_MEMBER_LOGON_EVENT = "org_member_logon"
    ORG_MEMBER_LOGOFF_EVENT = "org_member_logoff"

    MAX_CACHE_AGE = 86400

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.buddy_service = registry.get_instance("buddy_service")
        self.public_channel_service = registry.get_instance("public_channel_service")
        self.access_service = registry.get_instance("access_service")
        self.org_pork_service = registry.get_instance("org_pork_service")
        self.event_service = registry.get_instance("event_service")
        self.character_service = registry.get_instance("character_service")

    def pre_start(self):
        self.event_service.register_event_type(self.ORG_MEMBER_LOGON_EVENT)
        self.event_service.register_event_type(self.ORG_MEMBER_LOGOFF_EVENT)
        self.access_service.register_access_level(self.ORG_ACCESS_LEVEL, 60, self.check_org_member)
        self.bot.add_packet_handler(BuddyAdded.id, self.handle_buddy_added)

    @setting(name="org_id", value="", description="Override the default org id (the bot will get the org id automatically--this setting is intended for development and testing only. use at your own risk. restart the bot after changing this setting)")
    def org_id(self):
        return NumberSettingType(allow_empty=True)

    @setting(name="org_name", value="", description="Allows the bot to remember the org name when it cannot determine it automatically")
    def org_name(self):
        return TextSettingType()

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS org_member (char_id INT NOT NULL PRIMARY KEY, mode VARCHAR(20) NOT NULL, last_seen INT NOT NULL DEFAULT 0)")

    @command(command="notify", params=[Const("off"), Character("character")], access_level="admin",
             description="Turn off online notification for a character")
    def notify_off_cmd(self, request, _, char):
        if not char.char_id:
            return "Could not find character <highlight>%s<end>." % char.name

        org_member = self.get_org_member(char.char_id)
        if not org_member or org_member.mode == self.MODE_REM_MANUAL:
            return "<highlight>%s<end> is not on the notify list." % char.name

        self.process_update(char.char_id, org_member.mode if org_member else None, self.MODE_REM_MANUAL)

        # fire org_member logoff event
        self.event_service.fire_event(self.ORG_MEMBER_LOGOFF_EVENT, org_member)

        return "<highlight>%s<end> has been removed from the notify list." % char.name

    @command(command="notify", params=[Const("on"), Character("character")], access_level="admin",
             description="Turn on online notification for a character")
    def notify_on_cmd(self, request, _, char):
        if not char.char_id:
            return "Could not find character <highlight>%s<end>." % char.name

        org_member = self.get_org_member(char.char_id)
        if org_member and (org_member.mode == self.MODE_ADD_AUTO or org_member.mode == self.MODE_ADD_MANUAL):
            return "<highlight>%s<end> is already on the notify list." % char.name

        self.process_update(char.char_id, org_member.mode if org_member else None, self.MODE_ADD_MANUAL)

        # fire org_member logon event
        if self.buddy_service.is_online(char.char_id):
            self.event_service.fire_event(self.ORG_MEMBER_LOGON_EVENT, self.get_org_member(char.char_id))

        return "<highlight>%s<end> has been added to the notify list." % char.name

    @command(command="orgmembers", params=[], access_level="admin",
             description="Show the list of org members")
    def org_members_cmd(self, request):
        data = self.db.query("SELECT p.*, o.char_id, o.mode FROM org_member o LEFT JOIN player p ON o.char_id = p.char_id")
        blob = ""
        for row in data:
            blob += self.text.format_char_info(row) + " " + row.mode + "\n"

        return ChatBlob("Org Members (%d)" % len(data), blob)

    @event(event_type="connect", description="Add members as buddies of the bot on startup")
    def handle_connect_event(self, event_type, event_data):
        for row in self.get_all_org_members():
            self.update_buddylist(row.char_id, row.mode)

    @event(event_type=ORG_MEMBER_LOGON_EVENT, description="Record last seen info")
    def handle_org_member_logon_event(self, event_type, event_data):
        self.update_last_seen(event_data.char_id)

    @event(event_type=ORG_MEMBER_LOGOFF_EVENT, description="Record last seen info")
    def handle_org_member_logoff_event(self, event_type, event_data):
        if self.bot.is_ready():
            self.update_last_seen(event_data.char_id)

    @timerevent(budatime="24h", description="Download the org_members roster")
    def download_org_roster_event(self, event_type, event_data):
        org_id = self.public_channel_service.get_org_id()
        if org_id:
            db_members = {}
            for row in self.get_all_org_members():
                db_members[row.char_id] = row.mode

            self.logger.info("Updating org_members roster for org_id %d" % org_id)
            org_info = self.org_pork_service.get_org_info(org_id)

            if not org_info:
                self.logger.warning("could not get roster info for org id '%d'" % org_id)
                return

            t = int(time.time())
            if org_info.last_modified < (t - self.MAX_CACHE_AGE):
                self.logger.warning("skipping roster update due to old cache")
                return

            for char_id, roster_member in org_info.org_members.items():
                db_member = db_members.get(char_id, None)

                if db_member:
                    del db_members[char_id]

                self.process_update(char_id, db_member, self.MODE_ADD_AUTO)

            for char_id, mode in db_members.items():
                self.process_update(char_id, mode, self.MODE_REM_AUTO)

    @event(PublicChannelService.ORG_MSG_EVENT, "Update org roster when characters join or leave")
    def org_msg_event(self, event_type, event_data):
        ext_msg = event_data.extended_message
        if [ext_msg.category_id, ext_msg.instance_id] == OrgActivityController.LEFT_ORG:
            self.process_org_msg(ext_msg.params[0], self.MODE_REM_MANUAL)
        elif [ext_msg.category_id, ext_msg.instance_id] == OrgActivityController.KICKED_FROM_ORG:
            self.process_org_msg(ext_msg.params[1], self.MODE_REM_MANUAL)
        elif [ext_msg.category_id, ext_msg.instance_id] == OrgActivityController.INVITED_TO_ORG:
            self.process_org_msg(ext_msg.params[1], self.MODE_ADD_MANUAL)
        elif [ext_msg.category_id, ext_msg.instance_id] == OrgActivityController.KICKED_INACTIVE_FROM_ORG:
            self.process_org_msg(ext_msg.params[1], self.MODE_REM_MANUAL)

    @event(event_type=PublicChannelService.ORG_CHANNEL_MESSAGE_EVENT, description="Automatically add chars that speak in the org channel to the org roster")
    def auto_add_org_members_event(self, event_type, event_data):
        org_member = self.get_org_member(event_data.char_id)
        old_mode = org_member.mode if org_member else None
        self.process_update(event_data.char_id, old_mode, self.MODE_ADD_AUTO)

    def handle_buddy_added(self, packet: BuddyAdded):
        org_member = self.get_org_member(packet.char_id)
        if org_member and (org_member.mode == self.MODE_ADD_AUTO or org_member.mode == self.MODE_ADD_MANUAL):
            if packet.online:
                self.event_service.fire_event(self.ORG_MEMBER_LOGON_EVENT, org_member)
            else:
                self.event_service.fire_event(self.ORG_MEMBER_LOGOFF_EVENT, org_member)

    def process_org_msg(self, char_name, new_mode):
        char_id = self.character_service.resolve_char_to_id(char_name)
        org_member = self.get_org_member(char_id)
        self.process_update(char_id, org_member.mode if org_member else None, new_mode)

    def get_org_member(self, char_id):
        return self.db.query_single("SELECT char_id, mode FROM org_member WHERE char_id = ?", [char_id])

    def get_all_org_members(self):
        return self.db.query("SELECT char_id, mode FROM org_member")

    def add_org_member(self, char_id, mode):
        self.update_buddylist(char_id, self.MODE_ADD_MANUAL)
        return self.db.exec("INSERT INTO org_member (char_id, mode, last_seen) VALUES (?, ?, ?)", [char_id, mode, 0])

    def remove_org_member(self, char_id):
        self.update_buddylist(char_id, self.MODE_REM_MANUAL)
        return self.db.exec("DELETE FROM org_member WHERE char_id = ?", [char_id])

    def update_org_member(self, char_id, mode):
        self.update_buddylist(char_id, mode)
        return self.db.exec("UPDATE org_member SET mode = ? WHERE char_id = ?", [mode, char_id])

    def check_org_member(self, char_id):
        return self.get_org_member(char_id) is not None

    def update_last_seen(self, char_id):
        return self.db.exec("UPDATE org_member SET last_seen = ? WHERE char_id = ?", [int(time.time()), char_id])

    def update_buddylist(self, char_id, mode):
        if mode in [self.MODE_ADD_MANUAL, self.MODE_ADD_AUTO]:
            self.buddy_service.add_buddy(char_id, self.ORG_BUDDY_TYPE)
        else:
            self.buddy_service.remove_buddy(char_id, self.ORG_BUDDY_TYPE)

    def process_update(self, char_id, old_mode, new_mode):
        if not old_mode:
            if new_mode == self.MODE_ADD_AUTO or new_mode == self.MODE_ADD_MANUAL:
                self.add_org_member(char_id, new_mode)
        elif old_mode == self.MODE_ADD_AUTO:
            if new_mode == self.MODE_REM_MANUAL:
                self.update_org_member(char_id, new_mode)
            elif new_mode == self.MODE_REM_AUTO:
                self.remove_org_member(char_id)
        elif old_mode == self.MODE_ADD_MANUAL:
            if new_mode == self.MODE_ADD_AUTO:
                self.update_org_member(char_id, new_mode)
            elif new_mode == self.MODE_REM_MANUAL:
                self.remove_org_member(char_id)
        elif old_mode == self.MODE_REM_MANUAL:
            if new_mode == self.MODE_ADD_MANUAL:
                self.update_org_member(char_id, new_mode)
            elif new_mode == self.MODE_REM_AUTO:
                self.remove_org_member(char_id)
