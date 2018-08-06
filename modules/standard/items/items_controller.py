from core.decorators import instance, command
from core.db import DB
from core.text import Text
from core.chat_blob import ChatBlob
from core.command_param_types import Int, Any, Regex


@instance()
class ItemsController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")

    @command(command="items", params=[Regex("page=#", "(\s+page=(\d+))?", is_optional=True, num_groups=2), Int("ql", is_optional=True), Any("search")], access_level="all",
             description="Search for an item", aliases=["i"])
    def items_cmd(self, channel, sender, reply, args):
        page = int(args[0][1] or 1)
        ql = args[1]
        search = args[2]

        page_size = 40
        offset = (page - 1) * page_size

        all_items = self.find_items(search, ql)
        items = self.sort_items(search, all_items)[offset:offset + page_size]
        cnt = len(items)

        if cnt == 0:
            if ql:
                return "No QL <highlight>%d<end> items found matching <highlight>%s<end>." % (ql, search)
            else:
                return "No items found matching <highlight>%s<end>." % search
        else:
            blob = ""
            blob += "Version: <highlight>%s<end>\n" % "unknown"
            if ql:
                blob += "Search: <highlight>QL %d %s<end>\n" % (ql, search)
            else:
                blob += "Search: <highlight>%s<end>\n" % search
            blob += "\n"
            blob += self.format_items(items, ql)
            blob += "\nItem DB rips created using the %s tool." % self.text.make_chatcmd("Budabot Items Extractor", "/start https://github.com/Budabot/ItemsExtractor")

            return ChatBlob("Item Search Results (%d - %d of %d)" % (offset + 1, min(offset + page_size, len(all_items)), len(all_items)), blob)

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
        sql = "SELECT * FROM aodb WHERE name LIKE ? UNION SELECT * FROM aodb WHERE name <EXTENDED_LIKE=1> ?"
        params = [name, name]
        if ql:
            sql += " AND lowql <= ? AND highql >= ?"
            params.append(ql)
            params.append(ql)

        sql += " ORDER BY name ASC, highql DESC"

        return self.db.query(*self.db.handle_extended_like(sql, params))

    def sort_items(self, search, items):
        search = search.lower()
        search_parts = search.split(" ")

        # if item name matches search exactly (case-insensitive) then priority = 0
        # if item name contains every whole word from search (case-insensitive) then priority = 1
        # +1 priority for each whole word from search that item name does not contain

        for row in items:
            row.priority = 0
            row_name = row.name.lower()
            if row_name != search:
                row.priority += 1
                row_parts = row_name.split(" ")
                for search_part in search_parts:
                    if search_part not in row_parts:
                        row.priority += 1

        items.sort(key=lambda x: x.priority, reverse=False)

        return items

    def get_by_item_id(self, item_id):
        return self.db.query_single("SELECT * FROM aodb WHERE highid = ? OR lowid = ? ORDER BY highid = ?", [item_id, item_id, item_id])

    def find_by_name(self, name, ql=None):
        if ql:
            return self.db.query_single("SELECT * FROM aodb WHERE name = ? AND lowql <= ? AND highql >= ? ORDER BY highid DESC", [name, ql, ql])
        else:
            return self.db.query_single("SELECT * FROM aodb WHERE name = ? ORDER BY highql DESC, highid DESC", [name])
