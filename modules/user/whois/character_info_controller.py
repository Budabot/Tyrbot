from core.decorators import instance, command
from core.db import DB
from core.text import Text
from core.commands.param_types import Any


@instance()
class CharacterHistoryController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.pork_manager = registry.get_instance("pork_manager")

    @command(command="whois", params=[Any("character")], access_level="all",
             description="Get whois information for a character", sub_command="list")
    def whois_cmd(self, channel, sender, reply, args):
        char_name = args[1].capitalize()
        whois = self.pork_manager.get_character_info(char_name)
        if whois:
            msg = "<highlight>%s<end> (%d/<green>%d<end>) %s %s" %\
                  (whois.name, whois.level, whois.ai_level, whois.faction, whois.profession)
            reply(msg)
        else:
            reply("Could not find whois info for character <highlight>%s<end>." % char_name)
