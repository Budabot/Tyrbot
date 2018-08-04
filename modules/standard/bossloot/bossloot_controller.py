from core.decorators import instance, command
from core.db import DB
from core.text import Text
from core.chat_blob import ChatBlob
from core.command_param_types import Int, Any, Regex


@instance()
class BosslootController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")

    @command(command="boss", params=[Any("search")], access_level="all",
             description="Show loot for a boss")
    def boss_cmd(self, channel, sender, reply, args):
        search = args[0]

        sql = "SELECT bossid, bossname, w.answer FROM boss_namedb b LEFT JOIN whereis w ON b.bossname = w.name WHERE bossname <EXTENDED_LIKE=0> ?"
        data = self.db.query(*self.db.handle_extended_like(sql, [search]))
        cnt = len(data)

        blob = ""
        for row in data:
            blob += self.format_boss(row)
            blob += "\n\n"

        reply(ChatBlob("Boss Search Results for '%s' (%d)" % (search, cnt), blob))

    @command(command="bossloot", params=[Any("search")], access_level="all",
             description="Show loot for a boss")
    def bossloot_cmd(self, channel, sender, reply, args):
        search = args[0]

        sql = "SELECT DISTINCT b2.bossid, b2.bossname, w.answer " \
              "FROM boss_lootdb b1 JOIN boss_namedb b2 ON b2.bossid = b1.bossid LEFT JOIN whereis w ON w.name = b2.bossname " \
              "WHERE b1.itemname <EXTENDED_LIKE=0> ?"
        data = self.db.query(*self.db.handle_extended_like(sql, [search]))
        cnt = len(data)

        blob = ""
        for row in data:
            blob += self.format_boss(row)
            blob += "\n\n"

        reply(ChatBlob("Bossloot Search Results for '%s' (%d)" % (search, cnt), blob))

    def format_boss(self, row):
        data = self.db.query("SELECT * FROM boss_lootdb b LEFT JOIN aodb a ON b.itemname = a.name WHERE b.bossid = ? ORDER BY b.itemname ASC", [row.bossid])

        blob = "<pagebreak>"
        blob += "<header2>%s<end>\n" % row.bossname
        blob += "Location: <highlight>%s<end>\n" % row.answer
        blob += "Loot: " + ", ".join(map(lambda x: self.text.make_item(x.lowid, x.highid, x.highql, x.name), data))

        return blob
