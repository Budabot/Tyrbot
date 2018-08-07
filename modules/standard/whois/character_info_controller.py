from core.decorators import instance, command
from core.db import DB
from core.text import Text
from core.command_param_types import Any, Character
from core.chat_blob import ChatBlob


@instance()
class CharacterInfoController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.pork_service = registry.get_instance("pork_service")
        self.character_service = registry.get_instance("character_service")

    @command(command="whois", params=[Character("character")], access_level="all",
             description="Get whois information for a character", aliases=["w"])
    def whois_cmd(self, request, char_name):
        char_info = self.pork_service.get_character_info(char_name)
        char_id = self.character_service.resolve_char_to_id(char_name)
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
            blob += "Status: %s\n" % ("<green>Active<end>" if char_id else "<red>Inactive<end>")
            more_info = self.text.paginate("More Info", blob, 5000, 1)[0]

            return self.text.format_char_info(char_info) + " " + more_info
        elif char_id:
            blob = "<notice>Note: Could not retrieve detailed info for character.<end>\n\n"
            blob += "Name: <highlight>%s<end>\n" % char_name
            blob += "Character ID: <highlight>%d<end>" % char_id
            return ChatBlob("Basic Info for %s" % char_name, blob)
        else:
            return "Could not find info for character <highlight>%s<end>." % char_name

    def get_full_name(self, char_info):
        name = ""
        if char_info.first_name:
            name += char_info.first_name + " "

        name += "\"" + char_info.name + "\""

        if char_info.last_name:
            name += " " + char_info.last_name

        return name
