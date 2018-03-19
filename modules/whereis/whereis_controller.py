from core.decorators import instance, command, event
from core.db import DB
from core.chat_blob import ChatBlob


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
        search = args[1]
        data = self.db.query("SELECT * FROM whereis WHERE name <ENHANCED_LIKE> ?", [search])
        if len(data) > 0:
            reply(ChatBlob("Search results for %s" % search, data[0].answer))
        else:
            reply("Could not find any results for your search")
