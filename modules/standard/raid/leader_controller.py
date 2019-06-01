from core.command_param_types import Const, Character, Options
from core.db import DB
from core.decorators import instance, command, timerevent, event, setting
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
    NOT_LEADER_MSG = "Error! You must be raid leader, or have higher access " \
                     "level than the raid leader to use this command."

    def __init__(self):
        self.leader = None
        self.last_activity = None
        self.echo = False

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.access_service: AccessService = registry.get_instance("access_service")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.bot: Tyrbot = registry.get_instance("bot")
        self.setting_service: SettingService = registry.get_instance("setting_service")

    @setting(name="leader_echo_color", value="#00FF00",
             description="Color with which the leader's messages will be echoed with")
    def leader_echo_color(self):
        return ColorSettingType()

    @setting(name="leader_auto_echo", value=True,
             description="If turned on, when someone assume the leader role, leader echo "
                         "will automatically be activated for said person")
    def leader_auto_echo(self):
        return BooleanSettingType()

    @command(command="leader", params=[], access_level="all",
             description="Show the current raid leader")
    def leader_show_command(self, _):
        if self.leader:
            return "The current raid leader is <highlight>%s<end>." % self.leader.name
        else:
            return "There is no current raid leader. Use <highlight><symbol>leader set<end> to become the raid leader."

    @command(command="leader", params=[Const("echo"), Options(["on", "off"])], access_level="all",
             description="Echo whatever the current leader types in channel, in a distinctive color")
    def leader_echo_command(self, request, _2, switch_to):
        if self.leader:
            if self.can_use_command(request.sender.char_id):
                self.echo = switch_to == "on"
                return "Leader echo for <highlight>%s<end> has been turned <highlight>%s<end>." % \
                       (self.leader.name, switch_to)
            else:
                return "Insufficient access level."
        elif self.leader is None and switch_to == "on":
            return "No current leader set, can't turn on leader echo."

    @command(command="leader", params=[Const("echo")], access_level="all",
             description="See the current status for leader echoing")
    def leader_echo_status_command(self, _1, _2):
        if self.leader:
            on_off = "on" if self.echo else "off"
            return "<highlight>%s<end> is set as leader, leader echo is <highlight>%s<end>" % \
                   (self.leader.name, on_off)
        return "No current leader set."

    @command(command="leader", params=[Const("clear")], access_level="all",
             description="Clear the current raid leader")
    def leader_clear_command(self, request, _):
        return self.set_raid_leader(request.sender, None)

    @command(command="leader", params=[Const("set")], access_level="all",
             description="Set (or unset) yourself as raid leader")
    def leader_set_self_command(self, request, _):
        return self.set_raid_leader(request.sender, request.sender)

    @command(command="leader", params=[Const("set", is_optional=True), Character("character")], access_level="all",
             description="Set another character as raid leader")
    def leader_set_other_command(self, request, _, char):
        if not char.char_id:
            return "Could not find <highlight>%s<end>." % char.name

        return self.set_raid_leader(request.sender, char)

    @timerevent(budatime="1h", description="Remove raid leader if raid leader hasn't been active for more than 1 hour")
    def leader_auto_remove(self, _1, _2):
        if self.last_activity:
            if self.last_activity - int(time.time()) > 3600:
                self.leader = None
                self.last_activity = None
                self.echo = False

                self.bot.send_private_channel_message("Raid leader has been automatically "
                                                      "cleared because of inactivity.")
                self.bot.send_org_message("Raid leader has been automatically cleared because of inactivity.")

    @event(PrivateChannelService.LEFT_PRIVATE_CHANNEL_EVENT, "Remove raid leader if raid leader leaves private channel")
    def leader_remove_on_leave_private(self, _, event_data):
        if self.leader:
            if self.leader.char_id == event_data.char_id:
                self.leader = None
                self.last_activity = None
                self.echo = False
                self.bot.send_private_channel_message("%s left private channel, and has been cleared as raid leader." %
                                                      self.character_service.resolve_char_to_name(event_data.char_id))

    @event(OrgMemberController.ORG_MEMBER_LOGOFF_EVENT, "Remove raid leader if raid leader logs off")
    def leader_remove_on_logoff(self, _, event_data):
        if self.leader:
            if self.leader.char_id == event_data.char_id:
                self.leader = None
                self.last_activity = None
                self.echo = False
                self.bot.send_org_message("%s has logged off, and has been cleared as raid leader." %
                                          self.character_service.resolve_char_to_name(event_data.char_id))

    @event(PrivateChannelService.PRIVATE_CHANNEL_MESSAGE_EVENT, "Echo leader messages from private channel", is_hidden=True)
    def leader_echo_private_event(self, _, event_data):
        if self.leader and self.echo:
            if self.leader.char_id == event_data.char_id:
                if self.setting_service.get("symbol").get_value() != event_data.message[0]:
                    self.leader_echo(event_data.char_id, event_data.message, "priv")

    @event(PublicChannelService.ORG_CHANNEL_MESSAGE_EVENT, "Echo leader messages from org channel", is_hidden=True)
    def leader_echo_org_event(self, _, event_data):
        if self.leader and self.echo:
            if self.leader.char_id == event_data.char_id:
                if self.setting_service.get("symbol").get_value() != event_data.message[0]:
                    self.leader_echo(event_data.char_id, event_data.message, "org")

    def leader_echo(self, char_id, message, channel):
        sender = self.character_service.resolve_char_to_name(char_id)
        color = self.setting_service.get("leader_echo_color").get_value()

        if channel == "org":
            self.bot.send_org_message("%s: <font color=%s>%s" % (sender, color, message))
        if channel == "priv":
            self.bot.send_private_channel_message("%s: <font color=%s>%s" % (sender, color, message))

        self.activity_done()

    def activity_done(self):
        self.last_activity = int(time.time())

    def can_use_command(self, char_id):
        if not self.leader or self.access_service.has_sufficient_access_level(char_id, self.leader.char_id):
            self.activity_done()
            return True

        return False

    def set_raid_leader(self, sender, set_to):
        if set_to is None:
            if not self.leader:
                return "There is no current raid leader."
            elif self.leader.char_id == sender.char_id:
                self.leader = None
                self.echo = False
                return "You have been removed as raid leader."
            elif self.can_use_command(sender.char_id):
                old_leader = self.leader
                self.leader = None
                self.echo = False
                self.bot.send_private_message(old_leader.char_id,
                                              "You have been removed as raid leader by <highlight>%s<end>."
                                              % sender.name)
                return "You have removed <highlight>%s<end> as raid leader." % old_leader.name
            else:
                return "You do not have a high enough access level to remove raid leader from <highlight>%s<end>." % \
                       self.leader.name
        elif sender.char_id == set_to.char_id:
            if not self.leader:
                self.leader = sender
                self.echo = self.setting_service.get("leader_auto_echo").get_value()
                reply = "You have been set as raid leader."
                if self.echo:
                    reply += " Leader echo is <green>enabled<end>."
                return reply
            elif self.leader.char_id == sender.char_id:
                self.leader = None
                self.echo = False
                return "You have been removed as raid leader."
            elif self.can_use_command(sender.char_id):
                old_leader = self.leader
                self.leader = sender
                self.echo = self.setting_service.get("leader_auto_echo").get_value()
                reply = "<highlight>%s<end> has taken raid leader from you." % sender.name
                if self.echo:
                    reply += " Leader echo is <green>enabled<end>."
                self.bot.send_private_message(old_leader.char_id, reply)
                reply = "You have taken raid leader from <highlight>%s<end>." % old_leader.name
                if self.echo:
                    reply += " Leader echo is <green>enabled<end>."
                return reply
            else:
                return "You do not have a high enough access level to take raid leader from <highlight>%s<end>." % \
                       self.leader.name
        else:
            if self.can_use_command(sender.char_id):
                self.leader = set_to
                self.echo = self.setting_service.get("leader_auto_echo").get_value()
                reply = "<highlight>%s<end> has set you as raid leader." % sender.name
                if self.echo:
                    reply += " Leader echo is <green>enabled<end>."
                self.bot.send_private_message(set_to.char_id, reply)
                reply = "<highlight>%s<end> has been set as raid leader by %s." % (set_to.name, sender.name)
                if self.echo:
                    reply += " Leader echo is <green>enabled<end>."
                return reply
            else:
                return "You do not have a high enough access level to take raid leader from <highlight>%s<end>." % \
                       self.leader.name
