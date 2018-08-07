from core.command_param_types import Const, Any, Character
from core.db import DB
from core.decorators import instance, command
from core.text import Text


@instance()
class LeaderController:
    def __init__(self):
        self.leader = None

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.access_service = registry.get_instance("access_service")
        self.character_service = registry.get_instance("character_service")

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
