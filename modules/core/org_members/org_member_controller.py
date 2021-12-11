from core.aochat.server_packets import BuddyAdded
from core.chat_blob import ChatBlob
from core.command_param_types import Character, Options, Const
from core.conn import Conn
from core.decorators import instance, event, timerevent, command
from core.dict_object import DictObject
from core.logger import Logger
import time

from core.public_channel_service import PublicChannelService
from core.standard_message import StandardMessage


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

    LEFT_ORG = [508, 45978487]
    KICKED_FROM_ORG = [508, 37093479]
    INVITED_TO_ORG = [508, 173558247]
    KICKED_INACTIVE_FROM_ORG = [508, 20908201]
    KICKED_ALIGNMENT_CHANGED = [501, 181448347]
    JOINED_ORG = [508, 5146599]

    MAX_CACHE_AGE = 86400

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.buddy_service = registry.get_instance("buddy_service")
        self.public_channel_service = registry.get_instance("public_channel_service")
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.access_service = registry.get_instance("access_service")
        self.org_pork_service = registry.get_instance("org_pork_service")
        self.event_service = registry.get_instance("event_service")
        self.character_service = registry.get_instance("character_service")

    def pre_start(self):
        self.event_service.register_event_type(self.ORG_MEMBER_LOGON_EVENT)
        self.event_service.register_event_type(self.ORG_MEMBER_LOGOFF_EVENT)

        self.access_service.register_access_level(self.ORG_ACCESS_LEVEL, 60, self.check_org_member)
        self.bot.register_packet_handler(BuddyAdded.id, self.handle_buddy_added)

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS org_member (char_id INT NOT NULL PRIMARY KEY,"
                     "mode VARCHAR(20) NOT NULL, org_id INT NOT NULL)")

        self.command_alias_service.add_alias("notify", "orgmember")
        self.command_alias_service.add_alias("orgmembers", "orgmember")
        self.command_alias_service.add_alias("updateorg", "orgmember update")

    @command(command="orgmember", params=[Options(["off", "rem", "remove"]), Character("character")], access_level="moderator",
             description="Manually remove a char from the org roster")
    def orgmember_remove_cmd(self, request, _, char):
        if not char.char_id:
            return StandardMessage.char_not_found(char.name)

        org_member = self.get_org_member(char.char_id)
        if not org_member or org_member.mode == self.MODE_REM_MANUAL:
            return f"<highlight>{char.name}</highlight> is not on the org roster."

        if not request.conn.org_id:
            return "This bot connection does not have an associated org."

        self.process_update(char.char_id, org_member.mode if org_member else None, self.MODE_REM_MANUAL, request.conn)

        # fire org_member logoff event
        self.event_service.fire_event(self.ORG_MEMBER_LOGOFF_EVENT, DictObject({"char_id": org_member.char_id,
                                                                                "name": char.name,
                                                                                "conn": request.conn}))

        return f"<highlight>{char.name}</highlight> has been manually removed from the org roster."

    @command(command="orgmember", params=[Options(["on", "add"]), Character("character")], access_level="moderator",
             description="Manually add a char to the org roster")
    def orgmember_add_cmd(self, request, _, char):
        if not char.char_id:
            return StandardMessage.char_not_found(char.name)

        org_member = self.get_org_member(char.char_id)
        if org_member and (org_member.mode == self.MODE_ADD_AUTO or org_member.mode == self.MODE_ADD_MANUAL):
            return f"<highlight>{char.name}</highlight> is already on the org roster."

        if not request.conn.org_id:
            return "This bot connection does not have an associated org."

        self.process_update(char.char_id, org_member.mode if org_member else None, self.MODE_ADD_MANUAL, request.conn)

        # fire org_member logon event
        if self.buddy_service.is_online(char.char_id):
            org_member = self.get_org_member(char.char_id)
            self.event_service.fire_event(self.ORG_MEMBER_LOGON_EVENT, DictObject({"char_id": org_member.char_id,
                                                                                   "name": char.name,
                                                                                   "conn": request.conn}))

        return f"<highlight>{char.name}</highlight> has been manually added to the org roster."

    @command(command="orgmember", params=[], access_level="moderator",
             description="Show the list of org members")
    def orgmember_list_cmd(self, request):
        data = self.db.query("SELECT p.*, o.char_id, o.mode FROM org_member o LEFT JOIN player p ON o.char_id = p.char_id ORDER BY name")
        blob = ""
        for row in data:
            blob += self.text.format_char_info(row) + " " + row.mode + "\n"

        return ChatBlob(f"Org Members ({len(data)})", blob)

    @command(command="orgmember", params=[Const("update")], access_level="moderator",
             description="Force an update of the org roster")
    def orgmember_update_cmd(self, request, _):
        if not self.bot.get_conns(lambda x: x.is_main and x.org_id):
            return "This bot does not belong to an org."

        request.reply("The org roster update is starting...")
        self.update_org_roster(max_cache_age=0)
        return "The org roster update has finished."

    @event(event_type="connect", description="Add members as buddies of the bot on startup", is_system=True)
    def handle_connect_event(self, event_type, event_data):
        for row in self.get_all_org_members():
            self.update_buddylist(row.char_id, row.mode)

    @timerevent(budatime="24h", description="Download the org_members roster", is_system=True)
    def download_org_roster_event(self, event_type, event_data):
        self.update_org_roster()

    def update_org_roster(self, max_cache_age=None):
        extra_org_ids = set()
        data = self.db.query("SELECT DISTINCT org_id FROM org_member")
        for row in data:
            extra_org_ids.add(row.org_id)

        db_members = {}
        for row in self.get_all_org_members():
            db_members[row.char_id] = row

        for _id, conn in self.bot.get_conns(lambda x: x.is_main and x.org_id):
            org_id = conn.org_id
            if org_id in extra_org_ids:
                extra_org_ids.remove(org_id)

            self.logger.info(f"Updating org_members roster for org_id '{org_id}'")
            org_info = self.org_pork_service.get_org_info(org_id, max_cache_age)

            if not org_info:
                self.logger.warning(f"Could not get roster info for org id '{org_id}'")
                return

            t = int(time.time())
            if org_info.last_modified < (t - self.MAX_CACHE_AGE):
                self.logger.warning("Skipping roster update due to old cache")
                return

            for char_id, roster_member in org_info.org_members.items():
                db_member = db_members.get(char_id, None)

                mode = None
                if db_member:
                    mode = db_member.mode
                    del db_members[char_id]

                self.process_update(char_id, mode, self.MODE_ADD_AUTO, conn)

            for char_id, db_member in db_members.items():
                if db_member.org_id == org_id:
                    self.process_update(char_id, db_member.mode, self.MODE_REM_AUTO, conn)

        # remove org members who no longer have a corresponding conn
        for org_id in extra_org_ids:
            # TODO remove from buddy list
            self.db.exec("DELETE FROM org_member WHERE org_id = ?", [org_id])

    @event(PublicChannelService.ORG_MSG_EVENT, "Update org roster when characters join or leave", is_system=True)
    def org_msg_event(self, event_type, event_data):
        ext_msg = event_data.extended_message
        if [ext_msg.category_id, ext_msg.instance_id] == self.LEFT_ORG:
            self.process_org_msg(ext_msg.params[0], self.MODE_REM_MANUAL, event_data.conn)
        elif [ext_msg.category_id, ext_msg.instance_id] == self.KICKED_FROM_ORG:
            self.process_org_msg(ext_msg.params[1], self.MODE_REM_MANUAL, event_data.conn)
        elif [ext_msg.category_id, ext_msg.instance_id] == self.INVITED_TO_ORG:
            self.process_org_msg(ext_msg.params[1], self.MODE_ADD_MANUAL, event_data.conn)
        elif [ext_msg.category_id, ext_msg.instance_id] == self.KICKED_INACTIVE_FROM_ORG:
            self.process_org_msg(ext_msg.params[1], self.MODE_REM_MANUAL, event_data.conn)
        elif [ext_msg.category_id, ext_msg.instance_id] == self.KICKED_ALIGNMENT_CHANGED:
            self.process_org_msg(ext_msg.params[0], self.MODE_REM_MANUAL, event_data.conn)
        elif [ext_msg.category_id, ext_msg.instance_id] == self.JOINED_ORG:
            self.process_org_msg(ext_msg.params[0], self.MODE_ADD_MANUAL, event_data.conn)

    @event(event_type=PublicChannelService.ORG_CHANNEL_MESSAGE_EVENT, description="Automatically add chars that speak in the org channel to the org roster",
           is_enabled=False)
    def auto_add_org_members_event(self, event_type, event_data):
        if event_data.char_id == 0:
            return

        org_member = self.get_org_member(event_data.char_id)
        if not org_member:
            old_mode = None
            # set as MODE_ADD_AUTO to prevent this from overriding !notify off settings
            self.process_update(event_data.char_id, old_mode, self.MODE_ADD_AUTO, event_data.conn)

    def handle_buddy_added(self, conn: Conn, packet: BuddyAdded):
        org_member = self.get_org_member(packet.char_id)
        if org_member and (org_member.mode == self.MODE_ADD_AUTO or org_member.mode == self.MODE_ADD_MANUAL):
            # TODO
            # when bot starts, buddy packets may be sent before conn knows what org it belongs to
            # resulting in a conn value of None here
            event_data = DictObject({
                "char_id": org_member.char_id,
                "name": self.character_service.get_char_name(packet.char_id),
                "conn": self.bot.get_conn_by_org_id(org_member.org_id)
            })

            if packet.online:
                self.event_service.fire_event(self.ORG_MEMBER_LOGON_EVENT, event_data)
            else:
                self.event_service.fire_event(self.ORG_MEMBER_LOGOFF_EVENT, event_data)

    def process_org_msg(self, char_name, new_mode, conn):
        char_id = self.character_service.resolve_char_to_id(char_name)
        org_member = self.get_org_member(char_id)
        self.process_update(char_id, org_member.mode if org_member else None, new_mode, conn)

    def get_org_member(self, char_id):
        return self.db.query_single("SELECT char_id, mode, org_id FROM org_member WHERE char_id = ?", [char_id])

    def get_org_members_by_org_id(self, org_id):
        return self.db.query("SELECT char_id, mode, org_id FROM org_member WHERE org_id = ?", [org_id])

    def get_all_org_members(self):
        return self.db.query("SELECT char_id, mode, org_id FROM org_member")

    def add_org_member(self, char_id, mode, org_id):
        self.update_buddylist(char_id, self.MODE_ADD_MANUAL)
        return self.db.exec("INSERT INTO org_member (char_id, mode, org_id) VALUES (?, ?, ?)", [char_id, mode, org_id])

    def remove_org_member(self, char_id):
        self.update_buddylist(char_id, self.MODE_REM_MANUAL)
        return self.db.exec("DELETE FROM org_member WHERE char_id = ?", [char_id])

    def update_org_member(self, char_id, mode, org_id):
        self.update_buddylist(char_id, mode)
        return self.db.exec("UPDATE org_member SET mode = ?, org_id = ? WHERE char_id = ?", [mode, org_id, char_id])

    def check_org_member(self, char_id):
        return self.get_org_member(char_id) is not None

    def update_buddylist(self, char_id, mode):
        if mode in [self.MODE_ADD_MANUAL, self.MODE_ADD_AUTO]:
            self.buddy_service.add_buddy(char_id, self.ORG_BUDDY_TYPE)
        else:
            self.buddy_service.remove_buddy(char_id, self.ORG_BUDDY_TYPE)

    def process_update(self, char_id, old_mode, new_mode, conn):
        if not char_id:
            raise Exception("char_id = 0; %s %s %s %s" % (char_id, old_mode, new_mode, conn))
        name = self.character_service.get_char_name(char_id)
        event_data = DictObject({"char_id": char_id, "name": name, "conn": conn})
        # TODO instead of manual vs auto, use a priority
        # highest priority is 1? or 100?
        # org_roster is priority `low`, orgmsg is priority `medium`, manual is priority `high`
        # lower priority cannot override higher priority, unless org_ids are different
        #   (to handle case where char is manually removed from one org, then auto added to a different org)
        # when mode matches, priority is set to new priority, even if lower
        # edge case: when mode is remove and priority is anything other than `high`, then just remove record
        # edge case: manually remove member from org when member is already part of a different org, just disallow it?
        if not old_mode:
            if new_mode == self.MODE_ADD_AUTO or new_mode == self.MODE_ADD_MANUAL:
                self.add_org_member(char_id, new_mode, conn.org_id)
        elif old_mode == self.MODE_ADD_AUTO:
            if new_mode == self.MODE_REM_MANUAL:
                self.update_org_member(char_id, new_mode, conn.org_id)
                self.event_service.fire_event(self.ORG_MEMBER_LOGOFF_EVENT, event_data)
            elif new_mode == self.MODE_REM_AUTO:
                self.remove_org_member(char_id)
                self.event_service.fire_event(self.ORG_MEMBER_LOGOFF_EVENT, event_data)
        elif old_mode == self.MODE_ADD_MANUAL:
            if new_mode == self.MODE_ADD_AUTO:
                self.update_org_member(char_id, new_mode, conn.org_id)
            elif new_mode == self.MODE_REM_MANUAL:
                self.remove_org_member(char_id)
                self.event_service.fire_event(self.ORG_MEMBER_LOGOFF_EVENT, event_data)
        elif old_mode == self.MODE_REM_MANUAL:
            if new_mode == self.MODE_ADD_MANUAL:
                self.update_org_member(char_id, new_mode, conn.org_id)
            elif new_mode == self.MODE_REM_AUTO:
                self.remove_org_member(char_id)
