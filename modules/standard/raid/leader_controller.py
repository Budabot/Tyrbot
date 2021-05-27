from core.command_param_types import Const, Character, Options
from core.conn import Conn
from core.db import DB
from core.decorators import instance, command, timerevent, event
from core.setting_types import ColorSettingType, BooleanSettingType
from core.text import Text
from core.tyrbot import Tyrbot
from core.access_service import AccessService
from core.lookup.character_service import CharacterService
from core.setting_service import SettingService
from core.private_channel_service import PrivateChannelService
from core.public_channel_service import PublicChannelService
from modules.core.org_members.org_member_controller import OrgMemberController
import time


@instance()
class LeaderController:
    NOT_LEADER_MSG = "Error! You must be raid leader, or have higher access level than the raid leader to use this command."
    NO_CURRENT_LEADER_MSG = "There is no current raid leader. Use <highlight><symbol>leader set</highlight> to become the raid leader."

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.access_service: AccessService = registry.get_instance("access_service")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.bot: Tyrbot = registry.get_instance("bot")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.raid_controller = registry.get_instance("raid_controller")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("leaderecho", "leader echo")

        self.setting_service.register(self.module_name, "leader_echo_color", "#00FF00", ColorSettingType(), "Color with which the leader's messages will be echoed with")
        self.setting_service.register(self.module_name, "leader_auto_echo", False, BooleanSettingType(),
                                      "If turned on, when someone assume the leader role, leader echo will automatically be activated for said person")

    @command(command="leader", params=[Const("echo", is_optional=True)], access_level="all",
             description="Show the current raid leader")
    def leader_show_command(self, request, _):
        leader = self.get_leader(request.conn)
        if leader:
            on_off = "on" if request.conn.data.leader_echo else "off"
            return "<highlight>%s</highlight> is set as leader, leader echo is <highlight>%s</highlight>." % \
                   (leader.name, on_off)
        else:
            return self.NO_CURRENT_LEADER_MSG

    @command(command="leader", params=[Const("echo"), Options(["on", "off"])], access_level="all",
             description="Echo whatever the current leader types in channel, in a distinctive color")
    def leader_echo_command(self, request, _2, switch_to):
        leader = self.get_leader(request.conn)
        if leader:
            if self.can_use_command(request.sender.char_id, request.conn):
                request.conn.data.leader_echo = (switch_to == "on")
                return "Leader echo for <highlight>%s</highlight> has been turned <highlight>%s</highlight>." % \
                       (leader.name, switch_to)
            else:
                return self.NOT_LEADER_MSG
        elif switch_to == "on":
            return self.NO_CURRENT_LEADER_MSG

    @command(command="leader", params=[Const("clear")], access_level="all",
             description="Clear the current raid leader")
    def leader_clear_command(self, request, _):
        return self.set_raid_leader(request.sender, None, request.conn)

    @command(command="leader", params=[Const("set")], access_level="all",
             description="Set (or unset) yourself as raid leader")
    def leader_set_self_command(self, request, _):
        leader = self.get_leader(request.conn)
        if leader and leader.char_id == request.sender.char_id:
            set_to = None
        else:
            set_to = request.sender

        return self.set_raid_leader(request.sender, set_to, request.conn)

    @command(command="leader", params=[Const("set", is_optional=True), Character("character")], access_level="all",
             description="Set another character as raid leader")
    def leader_set_other_command(self, request, _, char):
        if not char.char_id:
            return "Could not find character <highlight>%s</highlight>." % char.name

        return self.set_raid_leader(request.sender, char, request.conn)

    @timerevent(budatime="1h", description="Remove raid leader if raid leader hasn't been active for more than 1 hour")
    def leader_auto_remove(self, event_type, event_data):
        for _id, conn in self.bot.get_conns():
            last_activity = conn.data.get("leader_last_activity")
            if last_activity:
                if last_activity - int(time.time()) > 3600:
                    self.clear_leader(conn)
                    self.raid_controller.send_message("Raid leader has been automatically cleared because of inactivity.", conn)

    @event(PrivateChannelService.LEFT_PRIVATE_CHANNEL_EVENT, "Remove raid leader if raid leader leaves private channel")
    def leader_remove_on_leave_private(self, event_type, event_data):
        leader = self.get_leader(event_data.conn)
        if leader:
            if leader.char_id == event_data.char_id:
                self.clear_leader(event_data.conn)
                self.raid_controller.send_message(f"{event_data.name} left private channel and has been automatically removed as raid leader.",
                                                  event_data.conn)

    @event(OrgMemberController.ORG_MEMBER_LOGOFF_EVENT, "Remove raid leader if raid leader logs off")
    def leader_remove_on_logoff(self, event_type, event_data):
        # fix for when buddy logs off before conn knows what org it belongs to
        if not event_data.conn:
            return

        leader = self.get_leader(event_data.conn)
        if leader:
            if leader.char_id == event_data.char_id:
                self.clear_leader(event_data.conn)
                self.raid_controller.send_message("%s has logged off and has been removed as raid leader." % event_data.name,
                                                  event_data.conn)

    @event(PrivateChannelService.PRIVATE_CHANNEL_MESSAGE_EVENT, "Echo leader messages from private channel", is_hidden=True)
    def leader_echo_private_event(self, event_type, event_data):
        leader = self.get_leader(event_data.conn)
        if leader and event_data.conn.data.leader_echo:
            if leader.char_id == event_data.char_id:
                if not event_data.message.startswith(self.setting_service.get("symbol").get_value()):
                    self.leader_echo(event_data.char_id, event_data.message, PrivateChannelService.PRIVATE_CHANNEL_COMMAND, conn=event_data.conn)

    @event(PublicChannelService.ORG_CHANNEL_MESSAGE_EVENT, "Echo leader messages from org channel", is_hidden=True)
    def leader_echo_org_event(self, event_type, event_data):
        leader = self.get_leader(event_data.conn)
        if leader and event_data.conn.data.leader_echo:
            if leader.char_id == event_data.char_id:
                if not event_data.message.startswith(self.setting_service.get("symbol").get_value()):
                    self.leader_echo(event_data.char_id, event_data.message, PublicChannelService.ORG_CHANNEL_COMMAND, event_data.conn)

    def leader_echo(self, char_id, message, channel, conn):
        sender = self.character_service.resolve_char_to_name(char_id)
        color = self.setting_service.get("leader_echo_color")

        if channel == PublicChannelService.ORG_CHANNEL_COMMAND:
            self.bot.send_org_message("%s: %s" % (sender, color.format_text(message)), conn=conn)
        elif channel == PrivateChannelService.PRIVATE_CHANNEL_COMMAND:
            self.bot.send_private_channel_message("%s: %s" % (sender, color.format_text(message)), conn=conn)

        self.activity_done(conn)

    def activity_done(self, conn):
        conn.data.leader_last_activity = int(time.time())

    def can_use_command(self, char_id, conn):
        leader = self.get_leader(conn)
        if not leader or self.access_service.has_sufficient_access_level(char_id, leader.char_id):
            self.activity_done(conn)
            return True

        return False

    def clear_leader(self, conn):
        conn.data.leader = None
        conn.data.leader_last_activity = None
        conn.data.leader_echo = False

    def get_leader(self, conn):
        return conn.data.get("leader")

    def set_leader(self, sender, conn):
        conn.data.leader = sender
        if conn.data.get("leader_echo") is None:
            conn.data.leader_echo = self.setting_service.get("leader_auto_echo").get_value()

    def set_raid_leader(self, sender, set_to, conn: Conn):
        leader = self.get_leader(conn)

        if set_to is None:
            if not leader:
                return "There is no current raid leader."
            elif leader.char_id == sender.char_id:
                self.clear_leader(conn)
                return "You have been removed as raid leader."
            elif self.can_use_command(sender.char_id, conn):
                self.clear_leader(conn)
                self.bot.send_private_message(leader.char_id,
                                              "You have been removed as raid leader by <highlight>%s</highlight>." % sender.name,
                                              conn=conn)
                return "You have removed <highlight>%s</highlight> as raid leader." % leader.name
            else:
                return "You do not have a high enough access level to remove raid leader from <highlight>%s</highlight>." % \
                       leader.name
        elif sender.char_id == set_to.char_id:
            if not leader:
                self.set_leader(sender, conn)
                reply = "You have been set as raid leader."
                if conn.data.leader_echo:
                    reply += " Leader echo is <green>enabled</green>."
                return reply
            elif leader.char_id == sender.char_id:
                self.clear_leader(conn)
                return "You have been removed as raid leader."
            elif self.can_use_command(sender.char_id, conn):
                self.set_leader(sender, conn)
                reply = "<highlight>%s</highlight> has taken raid leader from you." % sender.name
                if conn.data.leader_echo:
                    reply += " Leader echo is <green>enabled</green>."
                self.bot.send_private_message(leader.char_id, reply, conn=conn)
                reply = "You have taken raid leader from <highlight>%s</highlight>." % leader.name
                if conn.data.leader_echo:
                    reply += " Leader echo is <green>enabled</green>."
                return reply
            else:
                return "You do not have a high enough access level to take raid leader from <highlight>%s</highlight>." % \
                       leader.name
        else:
            if self.can_use_command(sender.char_id, conn):
                self.set_leader(set_to, conn)
                reply = "<highlight>%s</highlight> has set you as raid leader." % sender.name
                if conn.data.leader_echo:
                    reply += " Leader echo is <green>enabled</green>."
                self.bot.send_private_message(set_to.char_id, reply, conn=conn)
                reply = "<highlight>%s</highlight> has been set as raid leader by %s." % (set_to.name, sender.name)
                if conn.data.leader_echo:
                    reply += " Leader echo is <green>enabled</green>."
                return reply
            else:
                return "You do not have a high enough access level to take raid leader from <highlight>%s</highlight>." % \
                       leader.name
