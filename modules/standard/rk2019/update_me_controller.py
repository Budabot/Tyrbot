import time

from core.command_param_types import Any
from core.decorators import instance, command
import re


@instance()
class UpdateMeController:
    def __init__(self):
        self.regexes = {"breed": re.compile(r"Breed: (.+)"),
                        "level": re.compile(r"Level: (\d+)"),
                        "gender": re.compile(r"Gender: (.+)"),
                        "faction": re.compile(r"Alignment: (.+)"),
                        "profession": re.compile(r"Profession: (.+)", re.MULTILINE),
                        "profession_title": re.compile(r"Profession title: (.+) \(TitleLevel \d\)"),
                        "ai_rank": re.compile(r"Defender rank: (.+)"),
                        "org_name": re.compile(r"Clan: (.+)"),
                        "org_rank_name": re.compile(r"Clan title:(.+)")}

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.pork_service = registry.get_instance("pork_service")

    @command(command="updateme", params=[Any("char_info")], access_level="all",
             description="Update whois for your character", extended_description="Select your character, press \"T\" to show your char info, then copy and paste the entire contents as the param to this command")
    def update_me_cmd(self, request, char_info):
        char_info_obj = self.pork_service.get_from_database(char_id=request.sender.char_id)
        char_info_obj.name = request.sender.name
        char_info_obj.dimension = self.bot.dimension
        char_info_obj.source = "updateme"
        char_info_obj.last_updated = int(time.time())

        for key, regex in self.regexes.items():
            result = regex.search(char_info)
            if result:
                char_info_obj[key] = result.group(1)

        self.pork_service.save_character_info(char_info_obj)

        return "Your character info has been updated."
