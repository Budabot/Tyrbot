from core.decorators import instance, command
from core.db import DB
from core.text import Text
from core.command_param_types import Any, Int


@instance()
class CharacterHistoryController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.pork_manager = registry.get_instance("pork_manager")

    @command(command="history", params=[Any("character"), Int("server_num", is_optional=True)], access_level="all",
             description="Get history of character")
    def handle_history_cmd1(self, channel, sender, reply, args):
        name = args[0].capitalize()
        server_num = args[1] if args[1] else 5
        reply(self.get_character_history(name, server_num))

    def get_character_history(self, name, server_num):
        return "<header>" + name + " (" + str(server_num) + ")<end>"

