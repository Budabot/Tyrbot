from core.command_param_types import Const, Any, Character
from core.db import DB
from core.decorators import instance, command, timerevent, event
from core.text import Text
from core.tyrbot import Tyrbot
from core.private_channel_service import PrivateChannelService
from modules.core.org_members.org_member_controller import OrgMemberController
import time


@instance()
class LeaderController:
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
             description="Show the current raidleader")
    def leader_show_command(self, request):
        if self.leader:
            return "The current raidleader is <highlight>%s<end>." % self.character_service.resolve_char_to_name(self.leader)
        else:
            return "There is no current raidleader."

    @command(command="leader", params=[Const("set")], access_level="all",
             description="Set yourself as raidleader")
    def leader_set_self_command(self, request, _):
        if self.leader == request.sender.char_id:
            self.leader = None
            return "You have been removed as raidleader."
        elif not self.leader:
            self.leader = request.sender.char_id
            return "You have been set as raidleader."
        elif self.access_service.has_sufficient_access_level(request.sender.char_id, self.leader):
            self.leader = request.sender.char_id
            return "You have taken leader from <highlight>%s<end>." % self.character_service.resolve_char_to_name(self.leader)
        else:
            return "You do not have a high enough access level to take raidleader from <highlight>%s<end>." % self.character_service.resolve_char_to_name(self.leader)

    @command(command="leader", params=[Const("set", is_optional=True), Character("character")], access_level="all",
             description="Set another character as raidleader")
    def leader_set_other_command(self, request, _, char):
        if not char.char_id:
            return "Could not find <highlight>%s<end>." % char.name

        if not self.leader or self.access_service.has_sufficient_access_level(request.sender.char_id, self.leader):
            self.leader = char.char_id
            return "<highlight>%s<end> has been set as raidleader." % char.name
        else:
            return "You do not have a high enough access level to take raidleader from <highlight>%s<end>." % self.character_service.resolve_char_to_name(self.leader)

    @timerevent(budatime="1h", description="Remove leader if leader hasn't been active for more than 1 hour")
    def leader_auto_remove(self, event_type, event_data):
        if self.last_activity:
            if self.last_activity - int(time.time()) > 3600:
                self.leader = None
                self.last_activity = None

                self.bot.send_private_channel_message("Leader has been automatically cleared because of inactivity.")
                self.bot.send_org_message("Leader has been automatically cleared because of inactivity.")

    @event(PrivateChannelService.LEFT_PRIVATE_CHANNEL_EVENT, "Remove leader if leader leaves private channel")
    def leader_remove_on_leave_private(self, event_type, event_data):
        if self.leader == event_data.char_id:
            self.leader = None
            self.last_activity = None
            self.bot.send_private_channel_message("%s left private channel, and has been cleared as leader." % self.character_service.resolve_char_to_name(event_data.char_id))

    @event(OrgMemberController.ORG_MEMBER_LOGOFF_EVENT, "Remove leader if leader logs off")
    def leader_remove_on_logoff(self, event_type, event_data):
        if self.leader == event_data.char_id:
            self.leader = None
            self.last_activity = None
            self.bot.send_org_message("%s has logged off, and has been cleared as leader." % self.character_service.resolve_char_to_name(event_data.char_id))

    def activity_done(self):
        self.last_activity = int(time.time())

    def can_use_command(self, char_id):
        self.leader

        if not self.leader or self.leader == char_id or self.access_service.has_sufficient_access_level(char_id, self.leader):
            self.activity_done()
            return True

        return False
