from core.decorators import instance, command, event
from core.db import DB
from core.text import Text
from core.chat_blob import ChatBlob


@instance()
class CharacterHistoryController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")

    @command("history", "^([^ ]+) (\d)$", "all")
    def handle_history_cmd1(self, command, channel, sender, reply, args):
        name = args[1].lower().capitalize()
        server_num = args[2]
        reply(self.get_character_history(name, server_num))

    @command("history", "^([^ ]+)$", "all")
    def handle_history_cmd2(self, command, channel, sender, reply, args):
        name = args[1].lower().capitalize()
        reply(self.get_character_history(name, 5))

    def get_character_history(self, name, server_num):
        return "<header>" + name + " (" + str(server_num) + ")<end>"

