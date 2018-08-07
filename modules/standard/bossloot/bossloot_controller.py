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
    def boss_cmd(self, request, search):
        sql = "SELECT b.id, b.name, w.answer FROM boss b LEFT JOIN whereis w ON b.name = w.name WHERE b.name <EXTENDED_LIKE=0> ?"
        data = self.db.query(*self.db.handle_extended_like(sql, [search]))
        cnt = len(data)

        blob = ""
        for row in data:
            blob += self.format_boss(row)
            blob += "\n\n"

        return ChatBlob("Boss Search Results for '%s' (%d)" % (search, cnt), blob)

    @command(command="bossloot", params=[Any("search")], access_level="all",
             description="Show loot for a boss")
    def bossloot_cmd(self, request, search):
        sql = "SELECT DISTINCT b2.id, b2.name, w.answer " \
              "FROM boss_loot b1 JOIN boss b2 ON b2.id = b1.boss_id LEFT JOIN whereis w ON w.name = b2.name " \
              "WHERE b1.item_name <EXTENDED_LIKE=0> ?"
        data = self.db.query(*self.db.handle_extended_like(sql, [search]))
        cnt = len(data)

        blob = ""
        for row in data:
            blob += self.format_boss(row)
            blob += "\n\n"

        return ChatBlob("Bossloot Search Results for '%s' (%d)" % (search, cnt), blob)

    def format_boss(self, row):
        data = self.db.query("SELECT * FROM boss_loot b LEFT JOIN aodb a ON b.item_name = a.name WHERE b.boss_id = ? ORDER BY b.item_name ASC", [row.id])

        blob = "<pagebreak>"
        blob += "<header2>%s<end>\n" % row.name
        blob += "Location: <highlight>%s<end>\n" % row.answer
        blob += "Loot: " + ", ".join(map(lambda x: self.text.make_item(x.lowid, x.highid, x.highql, x.name), data))

        return blob
