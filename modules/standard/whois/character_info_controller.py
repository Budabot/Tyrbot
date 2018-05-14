from core.decorators import instance, command
from core.db import DB
from core.text import Text
from core.command_param_types import Any
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
        char_name = args[0].capitalize()
        char_info = self.pork_manager.get_character_info(char_name)
        char_id = self.character_manager.resolve_char_to_id(char_name)
        if char_info:
            blob = "Name: %s\n" % self.get_full_name(char_info)
            blob += "Profession: %s\n" % char_info.profession
            blob += "Faction: %s\n" % char_info.faction
            blob += "Breed: %s\n" % char_info.breed
            blob += "Gender: %s\n" % char_info.gender
            blob += "Level: %d\n" % char_info.level
            blob += "AI Level: %d\n" % char_info.ai_level
            if char_info.org_id:
                blob += "Org: %s (%d)\n" % (char_info.org_name, char_info.org_id)
                blob += "Org Rank: %s (%d)\n" % (char_info.org_rank_name, char_info.org_rank_id)
            else:
                blob += "Org: &lt;None&gt;\n"
                blob += "Org Rank: &lt;None&gt;\n"
            blob += "Head Id: %d\n" % char_info.head_id
            blob += "PVP Rating: %d\n" % char_info.pvp_rating
            blob += "PVP Title: %s\n" % char_info.pvp_title
            blob += "Character Id: %d\n" % char_info.char_id
            blob += "Source: %s\n" % char_info.source
            more_info = self.text.paginate("More Info", blob, 5000, 1)[0]

            msg = self.format_char_info(char_info) + " " + more_info
            reply(msg)
        elif char_id:
            blob = "<notice>Note: Could not retrieve detailed info for character.<end>\n\n"
            blob += "Name: <highlight>%s<end>\n" % char_name
            blob += "Character ID: <highlight>%d<end>" % char_id
            reply(ChatBlob("Basic Info for %s" % char_name, blob))
        else:
            reply("Could not find info for character <highlight>%s<end>." % char_name)

    def get_full_name(self, char_info):
        name = ""
        if char_info.first_name:
            name += char_info.first_name + " "

        name += "\"" + char_info.name + "\""

        if char_info.last_name:
            name += " " + char_info.last_name

        return name

    def format_char_info(self, char_info):
        if char_info.org_name and char_info.org_rank_name:
            return "<highlight>%s<end> (%d/<green>%d<end>) %s %s, %s of %s" % \
                   (char_info.name, char_info.level, char_info.ai_level, char_info.faction, char_info.profession, char_info.org_rank_name, char_info.org_name)
        else:
            return "<highlight>%s<end> (%d/<green>%d<end>) %s %s" % (char_info.name, char_info.level, char_info.ai_level, char_info.faction, char_info.profession)
