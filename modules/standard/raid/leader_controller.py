from core.command_param_types import Const, Any
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
    def leader_show_command(self, channel, sender, reply, args):
        if self.leader:
            reply("The current raidleader is <highlight>%s<end>." % self.character_service.resolve_char_to_name(self.leader))
        else:
            reply("There is no current raidleader.")

    @command(command="leader", params=[Const("set")], access_level="all",
             description="Set yourself as raidleader")
    def leader_set_self_command(self, channel, sender, reply, args):
        if self.leader == sender.char_id:
            reply("You have been removed as raidleader.")
            self.leader = None
        elif not self.leader:
            reply("You have been set as raidleader.")
            self.leader = sender.char_id
        elif self.access_service.has_sufficient_access_level(sender.char_id, self.leader):
            reply("You have taken leader from <highlight>%s<end>." % self.character_service.resolve_char_to_name(self.leader))
            self.leader = sender.char_id
        else:
            reply("You do not have a high enough access level to take raidleader from <highlight>%s<end>." % self.character_service.resolve_char_to_name(self.leader))

    @command(command="leader", params=[Const("set", is_optional=True), Any("character")], access_level="all",
             description="Set another character as raidleader")
    def leader_set_other_command(self, channel, sender, reply, args):
        char_name = args[1].capitalize()
        char_id = self.character_service.resolve_char_to_id(char_name)

        if not char_id:
            reply("Could not find <highlight>%s<end>." % char_name)
            return

        if not self.leader or self.access_service.has_sufficient_access_level(sender.char_id, self.leader):
            reply("<highlight>%s<end> has been set as raidleader." % char_name)
            self.leader = char_id
        else:
            reply("You do not have a high enough access level to take raidleader from <highlight>%s<end>." % self.character_service.resolve_char_to_name(self.leader))
