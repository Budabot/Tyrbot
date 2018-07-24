from core.chat_blob import ChatBlob
from core.decorators import instance, command
from core.command_param_types import Any, Int


@instance()
class CharacterHistoryController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.util = registry.get_instance("util")
        self.character_history_service = registry.get_instance("character_history_service")

    @command(command="history", params=[Any("character"), Int("server_num", is_optional=True)], access_level="all",
             description="Get history of character")
    def handle_history_cmd1(self, channel, sender, reply, args):
        name = args[0].capitalize()
        server_num = args[1] or self.bot.dimension

        data = self.character_history_service.get_character_history(name, server_num)
        if not data:
            reply("Could not find history for <highlight>%s<end> on server <highlight>%d<end>." % (name, server_num))
            return

        reply(ChatBlob("History of %s (RK%d)" % (name, server_num), self.format_character_history(name, data)))

    def format_character_history(self, name, history):
        blob = "Date           Level    AI     Faction    Breed        Guild (rank)\n"
        blob += "________________________________________________ \n"
        for row in history:
            if row.guild_name:
                org = "%s (%s)" % (row.guild_name, row.guild_rank_name)
            else:
                org = ""

            last_changed = self.util.format_timestamp(int(float(row.last_changed)), include_time=False)

            blob += "%s |  %s  | <green>%s<end> | %s | %s | %s\n" % \
                    (last_changed, row.level, row.defender_rank or 0, row.faction, row.breed, org)

        blob += "\nHistory provided by Auno.org, Chrisax, and Athen Paladins"

        return blob
