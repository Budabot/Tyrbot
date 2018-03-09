from core.decorators import instance, command
from core.db import DB
from core.command_manager import CommandManager


@instance()
class WhereisController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.command_manager: CommandManager = registry.get_instance("command_manager")

    def start(self):
        # with open("./modules/whereis/whereis.sql", "r") as f:
        #    self.db.load_sql(f.read())
        self.command_manager.register(self.handle_whereis, "whereis", "all", "^(\d+)$")

    # @command("whereis", "^(.+)$")
    def handle_whereis(self, command, channel, sender, reply, args):
        # data = self.db.query("SELECT * FROM whereis WHERE name LIKE ?", [args[1]])
        # reply(data[0]["answer"])
        reply("hi there")
