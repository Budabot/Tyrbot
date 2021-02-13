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
        self.raid_controller = registry.get_instance("raid_controller")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("leaderecho", "leader echo")

        self.setting_service.register(self.module_name, "leader_echo_color", "#00FF00", ColorSettingType(), "Color with which the leader's messages will be echoed with")
        self.setting_service.register(self.module_name, "leader_auto_echo", False, BooleanSettingType(),
                                      "If turned on, when someone assume the leader role, leader echo will automatically be activated for said person")

    @command(command="leader", params=[], access_level="all",
             description="Show the current raid leader")
    def leader_show_command(self, _):
        if self.leader:
            return "The current raid leader is <highlight>%s</highlight>." % self.leader.name
        else:
            return "There is no current raid leader. Use <highlight><symbol>leader set</highlight> to become the raid leader."

    @command(command="leader", params=[Const("echo"), Options(["on", "off"])], access_level="all",
             description="Echo whatever the current leader types in channel, in a distinctive color")
    def leader_echo_command(self, request, _2, switch_to):
        if self.leader:
            if self.can_use_command(request.sender.char_id):
                self.echo = switch_to == "on"
                return "Leader echo for <highlight>%s</highlight> has been turned <highlight>%s</highlight>." % \
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
            return "<highlight>%s</highlight> is set as leader, leader echo is <highlight>%s</highlight>." % \
                   (self.leader.name, on_off)
        return "No current leader set."

    @command(command="leader", params=[Const("clear")], access_level="all",
             description="Clear the current raid leader")
    def leader_clear_command(self, request, _):
        return self.set_raid_leader(request.sender, None)

    @command(command="leader", params=[Const("set")], access_level="all",
             description="Set (or unset) yourself as raid leader")
    def leader_set_self_command(self, request, _):
        if self.leader and self.leader.char_id == request.sender.char_id:
            set_to = None
        else:
            set_to = request.sender

        return self.set_raid_leader(request.sender, set_to)

    @command(command="leader", params=[Const("set", is_optional=True), Character("character")], access_level="all",
             description="Set another character as raid leader")
    def leader_set_other_command(self, request, _, char):
        if not char.char_id:
            return "Could not find <highlight>%s</highlight>." % char.name

        return self.set_raid_leader(request.sender, char)

    @timerevent(budatime="1h", description="Remove raid leader if raid leader hasn't been active for more than 1 hour")
    def leader_auto_remove(self, _1, _2):
        if self.last_activity:
            if self.last_activity - int(time.time()) > 3600:
                self.leader = None
                self.last_activity = None
                self.echo = False

                self.raid_controller.send_message("Raid leader has been automatically cleared because of inactivity.")

    @event(PrivateChannelService.LEFT_PRIVATE_CHANNEL_EVENT, "Remove raid leader if raid leader leaves private channel")
    def leader_remove_on_leave_private(self, _, event_data):
        if self.leader:
            if self.leader.char_id == event_data.char_id:
                self.leader = None
                self.last_activity = None
                self.echo = False
                # TODO add conn
                self.bot.send_private_channel_message("%s left private channel, and has been cleared as raid leader." %
                                                      self.character_service.resolve_char_to_name(event_data.char_id))

    @event(OrgMemberController.ORG_MEMBER_LOGOFF_EVENT, "Remove raid leader if raid leader logs off")
    def leader_remove_on_logoff(self, _, event_data):
        if self.leader:
            if self.leader.char_id == event_data.char_id:
                self.leader = None
                self.last_activity = None
                self.echo = False
                # TODO add conn
                self.bot.send_org_message("%s has logged off, and has been cleared as raid leader." %
                                          self.character_service.resolve_char_to_name(event_data.char_id))

    @event(PrivateChannelService.PRIVATE_CHANNEL_MESSAGE_EVENT, "Echo leader messages from private channel", is_hidden=True)
    def leader_echo_private_event(self, _, event_data):
        if self.leader and self.echo:
            if self.leader.char_id == event_data.char_id:
                if not event_data.message.startswith(self.setting_service.get("symbol").get_value()):
                    self.leader_echo(event_data.char_id, event_data.message, "priv")

    @event(PublicChannelService.ORG_CHANNEL_MESSAGE_EVENT, "Echo leader messages from org channel", is_hidden=True)
    def leader_echo_org_event(self, _, event_data):
        if self.leader and self.echo:
            if self.leader.char_id == event_data.char_id:
                if not event_data.message.startswith(self.setting_service.get("symbol").get_value()):
                    self.leader_echo(event_data.char_id, event_data.message, "org")

    def leader_echo(self, char_id, message, channel):
        sender = self.character_service.resolve_char_to_name(char_id)
        color = self.setting_service.get("leader_echo_color")

        if channel == "org":
            # TODO add conn
            self.bot.send_org_message("%s: %s" % (sender, color.format_text(message)), fire_outgoing_event=False)
        elif channel == "priv":
            # TODO add conn
            self.bot.send_private_channel_message("%s: %s" % (sender, color.format_text(message)), fire_outgoing_event=False)

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
                # TODO add conn
                self.bot.send_private_message(old_leader.char_id,
                                              "You have been removed as raid leader by <highlight>%s</highlight>."
                                              % sender.name)
                return "You have removed <highlight>%s</highlight> as raid leader." % old_leader.name
            else:
                return "You do not have a high enough access level to remove raid leader from <highlight>%s</highlight>." % \
                       self.leader.name
        elif sender.char_id == set_to.char_id:
            if not self.leader:
                self.leader = sender
                self.echo = self.setting_service.get("leader_auto_echo").get_value()
                reply = "You have been set as raid leader."
                if self.echo:
                    reply += " Leader echo is <green>enabled</green>."
                return reply
            elif self.leader.char_id == sender.char_id:
                self.leader = None
                self.echo = False
                return "You have been removed as raid leader."
            elif self.can_use_command(sender.char_id):
                old_leader = self.leader
                self.leader = sender
                self.echo = self.setting_service.get("leader_auto_echo").get_value()
                reply = "<highlight>%s</highlight> has taken raid leader from you." % sender.name
                if self.echo:
                    reply += " Leader echo is <green>enabled</green>."
                # TODO add conn
                self.bot.send_private_message(old_leader.char_id, reply)
                reply = "You have taken raid leader from <highlight>%s</highlight>." % old_leader.name
                if self.echo:
                    reply += " Leader echo is <green>enabled</green>."
                return reply
            else:
                return "You do not have a high enough access level to take raid leader from <highlight>%s</highlight>." % \
                       self.leader.name
        else:
            if self.can_use_command(sender.char_id):
                self.leader = set_to
                self.echo = self.setting_service.get("leader_auto_echo").get_value()
                reply = "<highlight>%s</highlight> has set you as raid leader." % sender.name
                if self.echo:
                    reply += " Leader echo is <green>enabled</green>."
                # TODO add conn
                self.bot.send_private_message(set_to.char_id, reply)
                reply = "<highlight>%s</highlight> has been set as raid leader by %s." % (set_to.name, sender.name)
                if self.echo:
                    reply += " Leader echo is <green>enabled</green>."
                return reply
            else:
                return "You do not have a high enough access level to take raid leader from <highlight>%s</highlight>." % \
                       self.leader.name
