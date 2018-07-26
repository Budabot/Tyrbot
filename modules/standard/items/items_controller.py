from core.decorators import instance, command
from core.db import DB
from core.text import Text
from core.chat_blob import ChatBlob
from core.command_param_types import Int, Any


@instance()
class ItemsController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")

    def start(self):
        pass

    @command(command="items", params=[Int("ql", is_optional=True), Any("search")], access_level="all",
             description="Search for an item", aliases=["i"])
    def items_cmd(self, channel, sender, reply, args):
        ql = args[0]
        search = args[1]

        items = self.find_items(search, ql)
        count = len(items)

        if count == 0:
            if ql:
                reply("No QL <highlight>%d<end> items found matching <highlight>%s<end>." % (ql, search))
            else:
                reply("No items found matching <highlight>%s<end>." % search)
        else:
            blob = ""
            blob += "Version: <highlight>%s<end>\n" % "unknown"
            if ql:
                blob += "Search: <highlight>QL %d %s<end>\n" % (ql, search)
            else:
                blob += "Search: <highlight>%s<end>\n" % search
            blob += "\n"
            blob += self.format_items(items, ql)
            blob += "Item DB rips created using the %s tool." % self.text.make_chatcmd("Budabot Items Extractor", "/start https://github.com/Budabot/ItemsExtractor")

            reply(ChatBlob("Item Search Results (%d)" % count, blob))

    def format_items(self, items, ql=None):
        blob = ""
        for item in items:
            blob += "<pagebreak>"
            blob += self.text.make_image(item.icon) + "\n"
            if ql:
                blob += "QL %d " % ql
                blob += self.text.make_item(item.lowid, item.highid, ql, item.name)
            else:
                blob += self.text.make_item(item.lowid, item.highid, item.highql, item.name)

            if item.lowql != item.highql:
                blob += " (QL%d - %d)\n" % (item.lowql, item.highql)
            else:
                blob += " (QL%d)\n" % item.highql

            blob += "\n"

        return blob

    def find_items(self, name, ql=None):
        sql = "SELECT * FROM aodb WHERE name <EXTENDED_LIKE=0> ?"
        params = [name]
        if ql:
            sql += " AND lowql <= ? AND highql >= ?"
            params.append(ql)
            params.append(ql)

        sql += " ORDER BY name ASC, highql DESC LIMIT 50"

        return self.db.query(*self.db.handle_extended_like(sql, params))

    def get_by_item_id(self, item_id):
        return self.db.query_single("SELECT * FROM aodb WHERE highid = ? OR lowid = ? ORDER BY highid = ?", [item_id, item_id, item_id])

    def find_by_name(self, name, ql=None):
        if ql:
            return self.db.query_single("SELECT * FROM aodb WHERE name = ? AND lowql <= ? AND highql >= ? ORDER BY highid DESC", [name, ql, ql])
        else:
            return self.db.query_single("SELECT * FROM aodb WHERE name = ? ORDER BY highql DESC, highid DESC", [name])
