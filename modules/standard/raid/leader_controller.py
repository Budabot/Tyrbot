from core.command_param_types import Const, Character
from core.db import DB
from core.decorators import instance, command, timerevent, event
from core.text import Text
from core.tyrbot import Tyrbot
from core.private_channel_service import PrivateChannelService
from modules.core.org_members.org_member_controller import OrgMemberController
import time


@instance()
class LeaderController:
    NOT_LEADER_MSG = "Error! You must be raid leader, or have higher access level than the raid leader to use this command."

    def __init__(self):
        self.leader = None
        self.last_activity = None

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.access_service = registry.get_instance("access_service")
        self.character_service = registry.get_instance("character_service")
        self.bot: Tyrbot = registry.get_instance("bot")

    @command(command="leader", params=[], access_level="all",
             description="Show the current raid leader")
    def leader_show_command(self, request):
        if self.leader:
            return "The current raid leader is <highlight>%s<end>." % self.leader.name
        else:
            return "There is no current raid leader. Use <highlight><symbol>leader set<end> to become the raid leader."

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
    def leader_auto_remove(self, event_type, event_data):
        if self.last_activity:
            if self.last_activity - int(time.time()) > 3600:
                self.leader = None
                self.last_activity = None

                self.bot.send_private_channel_message("Raid leader has been automatically cleared because of inactivity.")
                self.bot.send_org_message("Raid leader has been automatically cleared because of inactivity.")

    @event(PrivateChannelService.LEFT_PRIVATE_CHANNEL_EVENT, "Remove raid leader if raid leader leaves private channel")
    def leader_remove_on_leave_private(self, event_type, event_data):
        if self.leader and self.leader.char_id == event_data.char_id:
            self.leader = None
            self.last_activity = None
            self.bot.send_private_channel_message("%s left private channel, and has been cleared as raid leader." % self.character_service.resolve_char_to_name(event_data.char_id))

    @event(OrgMemberController.ORG_MEMBER_LOGOFF_EVENT, "Remove raid leader if raid leader logs off")
    def leader_remove_on_logoff(self, event_type, event_data):
        if self.leader and self.leader.char_id == event_data.char_id:
            self.leader = None
            self.last_activity = None
            self.bot.send_org_message("%s has logged off, and has been cleared as raid leader." % self.character_service.resolve_char_to_name(event_data.char_id))

    def activity_done(self):
        self.last_activity = int(time.time())

    def can_use_command(self, char_id):
        if not self.leader or self.access_service.has_sufficient_access_level(char_id, self.leader.char_id):
            self.activity_done()
            return True

        return False

    def set_raid_leader(self, sender, settee):
        if settee is None:
            if not self.leader:
                return "There is no current raid leader."
            elif self.leader.char_id == sender.char_id:
                self.leader = None
                return "You have been removed as raid leader."
            elif self.access_service.has_sufficient_access_level(sender.char_id, self.leader.char_id):
                old_leader = self.leader
                self.leader = None
                self.bot.send_private_message(old_leader.char_id, "You have been removed as raid leader by <highlight>%s<end>." % sender.name)
                return "You have removed <highlight>%s<end> as raid leader." % old_leader.name
            else:
                return "You do not have a high enough access level to remove raid leader from <highlight>%s<end>." % self.leader.name
        elif sender.char_id == settee.char_id:
            if not self.leader:
                self.leader = sender
                return "You have been set as raid leader."
            elif self.leader.char_id == sender.char_id:
                self.leader = None
                return "You have been removed as raid leader."
            elif self.access_service.has_sufficient_access_level(sender.char_id, self.leader.char_id):
                old_leader = self.leader
                self.leader = sender
                self.bot.send_private_message(old_leader.char_id, "<highlight>%s<end> has taken raid leader from you." % sender.name)
                return "You have taken raid leader from <highlight>%s<end>." % old_leader.name
            else:
                return "You do not have a high enough access level to take raid leader from <highlight>%s<end>." % self.leader.name
        else:
            if not self.leader or self.access_service.has_sufficient_access_level(sender.char_id, self.leader.char_id):
                self.leader = settee
                self.bot.send_private_message(settee.char_id, "<highlight>%s<end> has set you as raid leader." % sender.name)
                return "<highlight>%s<end> has been set as raid leader." % settee.name
            else:
                return "You do not have a high enough access level to take raid leader from <highlight>%s<end>." % self.leader.name
