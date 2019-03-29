import time

from core.command_param_types import Any
from core.decorators import instance, command
import re

from core.dict_object import DictObject


@instance()
class UpdateMeController:
    def __init__(self):
        self.regexes = [DictObject({"name": "breed", "regex": re.compile(r"Breed: (.+)")}),
                        DictObject({"name": "level", "regex": re.compile(r"Level: (\d+)")}),
                        DictObject({"name": "gender", "regex": re.compile(r"Gender: (.+)")}),
                        DictObject({"name": "faction", "regex": re.compile(r"Alignment: (.+)")}),
                        DictObject({"name": "profession", "regex": re.compile(r"Profession: (.+)", re.MULTILINE)}),
                        DictObject({"name": "profession_title", "regex": re.compile(r"Profession title: (.+) \(TitleLevel \d\)")}),
                        DictObject({"name": "ai_rank", "regex": re.compile(r"Defender rank: (.+)")}),
                        DictObject({"name": "org_name", "regex": re.compile(r"Clan: (.+)")}),
                        DictObject({"name": "org_name", "regex": re.compile(r"Detachment: (.+)")}),
                        DictObject({"name": "org_rank_name", "regex": re.compile(r"Detachment title:(.+)")}),
                        DictObject({"name": "org_rank_name", "regex": re.compile(r"Clan title:(.+)")})]

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.pork_service = registry.get_instance("pork_service")

    @command(command="updateme", params=[Any("char_info")], access_level="all",
             description="Update whois for your character", extended_description="Select your character, press \"T\" to show your char info, then copy and paste the entire contents as the param to this command")
    def update_me_cmd(self, request, char_info):
        if self.bot.dimension == 5:
            return "This command cannot be used on this server."

        newline = re.compile(r"\n")
        result = newline.search(char_info)
        if not result:
            return "This command must be used from a tell window (click the bot name in chat to open a tell window)."

        char_info_obj = self.pork_service.get_from_database(char_id=request.sender.char_id)
        char_info_obj.name = request.sender.name
        char_info_obj.dimension = self.bot.dimension
        char_info_obj.source = "updateme"
        char_info_obj.last_updated = int(time.time())

        for item in self.regexes:
            result = item.regex.search(char_info)
            if result:
                char_info_obj[item.name] = result.group(1)

        if char_info_obj.faction:
            char_info_obj.faction = char_info_obj.faction.capitalize()

        self.pork_service.save_character_info(char_info_obj)

        return "Your character info has been updated."
