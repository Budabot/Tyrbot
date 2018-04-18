from core.decorators import instance, command
from core.db.db import DB
from core.text import Text
from core.commands.param_types import Any
from core.chat_blob import ChatBlob


@instance()
class CharacterInfoController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.pork_manager = registry.get_instance("pork_manager")
        self.character_manager = registry.get_instance("character_manager")

    @command(command="whois", params=[Any("character")], access_level="all",
             description="Get whois information for a character")
    def whois_cmd(self, channel, sender, reply, args):
        char_name = args[1].capitalize()
        whois = self.pork_manager.get_character_info(char_name)
        char_id = self.character_manager.resolve_char_to_id(char_name)
        if whois:
            # TODO add extended info
            msg = "<highlight>%s<end> (%d/<green>%d<end>) %s %s" % (whois.name, whois.level, whois.ai_level, whois.faction, whois.profession)
            reply(msg)
        elif char_id:
            blob = "<notice>Note: Could not retrieve detailed info for character.<end>\n\n"
            blob += "Name: <highlight>%s<end>\n" % char_name
            blob += "Character ID: <highlight>%d<end>" % char_id
            reply(ChatBlob("Basic Info for %s" % char_name, blob))
        else:
            reply("Could not find info for character <highlight>%s<end>." % char_name)
