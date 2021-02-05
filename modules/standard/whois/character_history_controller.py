from core.chat_blob import ChatBlob
from core.command_param_types import Int, Character
from core.decorators import instance, command


@instance()
class CharacterHistoryController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.text = registry.get_instance("text")
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
        spacing = [90, 30, 18, 50, 65, 95]
        col_separator = " | "

        headers = [self.text.pad("Date", spacing[0]),
                   self.text.pad("Lvl", spacing[1]),
                   self.text.pad("AI", spacing[2]),
                   self.text.pad("Side", spacing[3]),
                   self.text.pad("Breed", spacing[4]),
                   self.text.pad("CharId", spacing[5]),
                   "Guild (Rank)"]

        blob = col_separator.join(headers) + "\n"
        blob += "__________________________________________________________\n"
        for row in history:
            if row.guild_name:
                org = "%s (%s)" % (row.guild_name, row.guild_rank_name)
            else:
                org = ""

            last_changed = self.util.format_date(int(float(row.last_changed)))
            if row.deleted == "1":  # This value is output as string
                blob += self.text.pad(last_changed, spacing[0]) + col_separator + "<red>DELETED</red>\n"
            else:
                cols = [self.text.pad(last_changed, spacing[0]),
                        self.text.pad(row.level, spacing[1]),
                        "<green>" + self.text.pad(row.defender_rank or 0, spacing[2]) + "</green>",
                        self.text.pad(row.faction, spacing[3]),
                        self.text.pad(row.breed, spacing[4]),
                        self.text.pad(row.char_id, spacing[5]),
                        org]
                blob += col_separator.join(cols) + "\n"
        blob += "\nHistory provided by Auno.org, Chrisax, and Athen Paladins"
        return blob
