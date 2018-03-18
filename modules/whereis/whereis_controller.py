from core.decorators import instance, command, event
from core.db import DB


@instance()
class WhereisController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")

    def start(self):
        self.db.load_sql_file("./modules/whereis/whereis.sql")

    @command("whereis", "^(.+)$", "all")
    def handle_whereis_cmd(self, command, channel, sender, reply, args):
        data = self.db.query("SELECT * FROM whereis WHERE name <ENHANCED_LIKE> ?", [args[1]])
        if len(data) > 0:
            reply(data[0]["answer"])
        else:
            reply("Could not find any results for your search")
