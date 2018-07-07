from core.decorators import instance, command
from core.db import DB
from core.text import Text
from core.chat_blob import ChatBlob


@instance()
class PlayfieldController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")

    @command(command="playfield", params=[], access_level="all",
             description="Show a list of playfields", aliases=["playfields"])
    def playfield_list_command(self, channel, sender, reply, args):
        data = self.db.query("SELECT * FROM playfields ORDER BY long_name")

        blob = ""
        for row in data:
            blob += "[<highlight>%d<end>] %s (%s)\n" % (row.id, row.long_name, row.short_name)

        reply(ChatBlob("Playfields", blob))

    def get_playfield_by_name(self, name):
        return self.db.query_single("SELECT * FROM playfields WHERE long_name LIKE ? OR short_name LIKE ? LIMIT 1", [name, name])

    def get_playfield_by_id(self, playfield_id):
        return self.db.query_single("SELECT * FROM playfields WHERE id = ?", [playfield_id])
