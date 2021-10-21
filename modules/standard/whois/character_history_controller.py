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

        return ChatBlob("History of %s (RK%d)" % (char.name, server_num), self.format_character_history(char.name, server_num, data))

    def format_character_history(self, name, server_num, history):
        col_separator = " | "

        rows = [["Name", "Date", "Lvl", "AI", "Side", "Breed", "CharId", "Org (Rank)"]]
        uniques = set()
        for row in history:
            if row.nickname and row.nickname != name:
                uniques.add(row.nickname)
            if row.char_id and row.char_id != name:
                uniques.add(row.char_id)

            if row.guild_name:
                org = "%s (%s)" % (row.guild_name, row.guild_rank_name)
            else:
                org = ""

            last_changed = self.util.format_date(int(float(row.last_changed)))
            current_row = [row.nickname, last_changed]

            if row.deleted == "1":  # This value is output as string
                current_row.append("<red>DELETED</red>")
            else:
                current_row.extend([row.level, "<green>%s</green>" % (row.defender_rank or "0"), row.faction, row.breed, row.char_id, org])

            rows.append(current_row)

        rows = self.text.pad_table(rows)
        blob = "  ".join(map(lambda x: "[" + self.text.make_tellcmd(f"History {x}", f"history {x} {server_num}") + "]", uniques)) + "\n\n"

        blob += col_separator.join(rows[0]) + "\n"
        blob += "__________________________________________________________\n"
        for columns in rows[1:]:
            blob += col_separator.join(columns) + "\n"

        blob += "\nHistory provided by Auno.org, Chrisax, and Athen Paladins"
        return blob
