from core.decorators import instance
from core.db import DB
from core.command_manager import CommandManager
import re


@instance()
class WhereisController:
    def __init__(self):
        self.whereis_regex = [[re.compile("^whereis (.+)$", re.IGNORECASE), self.whereis_search]]

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.command_manager: CommandManager = registry.get_instance("command_manager")

    def start(self):
        with open("./modules/whereis/whereis.sql", "r") as f:
            self.db.load_sql(f.read())
        self.command_manager.register(self.handle_whereis, "whereis", "all")

    def handle_whereis(self, command, channel, sender, reply, args):
        for [regex, handler] in self.whereis_regex:
            matches = regex.match(command)
            if matches:
                return handler(command, channel, sender, reply, matches)
        return False

    def whereis_search(self, command, channel, sender, reply, args):
        reply("This is SPARTA!")
