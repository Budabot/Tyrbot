from core.chat_blob import ChatBlob
from core.command_param_types import Int, Character
from core.decorators import instance, command


@instance()
class CharacterHistoryController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.util = registry.get_instance("util")
        self.character_history_service = registry.get_instance("character_history_service")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("h", "history")

    @command(command="history", params=[Character("character"), Int("server_num", is_optional=True)], access_level="all",
             description="Get history of character", extended_description="Use server_num 6 for RK2019 and server_num 5 for live")
    def handle_history_cmd1(self, request, char, server_num):
        server_num = server_num or self.bot.dimension

        data = self.character_history_service.get_character_history(char.name, server_num)
        if not data:
            return "Could not find history for <highlight>%s</highlight> on server <highlight>%d</highlight>." % (char.name, server_num)

        return ChatBlob("History of %s (RK%d)" % (char.name, server_num), self.format_character_history(data))

    def format_character_history(self, history):
        blob = "Date           Level    AI     Faction    Breed     CharId     Guild (rank)\n"
        blob += "________________________________________________ \n"
        for row in history:
            if row.guild_name:
                org = "%s (%s)" % (row.guild_name, row.guild_rank_name)
            else:
                org = ""

            last_changed = self.util.format_date(int(float(row.last_changed)))
            if row.deleted == "1":  # This value is output as string
                blob += "%s |  <red>DELETED</red>\n" % last_changed
            else:
                blob += "%s |  %s  | <green>%s</green> | %s | %s | %s | %s\n" % \
                    (last_changed, row.level, row.defender_rank or 0, row.faction, row.breed, row.char_id or "           ", org)
        blob += "\nHistory provided by Auno.org, Chrisax, and Athen Paladins"
        return blob
