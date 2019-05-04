import html

from core.chat_blob import ChatBlob
from core.command_param_types import Int, Any, NamedParameters
from core.db import DB
from core.decorators import instance, command
from core.text import Text


@instance()
class ItemsController:
    PAGE_SIZE = 30

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("item", "items")
        self.command_alias_service.add_alias("i", "items")

    @command(command="items", params=[Int("item_id")], access_level="all",
             description="Search for an item by item id")
    def items_id_cmd(self, request, item_id):
        item = self.get_by_item_id(item_id)
        if item:
            return self.format_items_response(None, str(item_id), [item], 0, 1)
        else:
            return "Could not find item with ID <highlight>%d<end>." % item_id

    @command(command="items", params=[Int("ql", is_optional=True), Any("search"), NamedParameters(["page"])], access_level="all",
             description="Search for an item")
    def items_search_cmd(self, request, ql, search, named_params):
        page = int(named_params.page or "1")

        search = html.unescape(search)

        offset = (page - 1) * self.PAGE_SIZE

        all_items = self.find_items(search, ql)

        return self.format_items_response(ql, search, all_items, offset, page)

    def format_items_response(self, ql, search, all_items, offset, page):
        items = self.sort_items(search, all_items)[offset:offset + self.PAGE_SIZE]
        cnt = len(items)

        if cnt == 0:
            if ql:
                return "No QL <highlight>%d<end> items found matching <highlight>%s<end>." % (ql, search)
            else:
                return "No items found matching <highlight>%s<end>." % search
        else:
            blob = ""
            # blob += "Version: <highlight>%s<end>\n" % "unknown"
            if ql:
                blob += "Search: <highlight>QL %d %s<end>\n" % (ql, search)
            else:
                blob += "Search: <highlight>%s<end>\n" % search
            blob += "\n"

            if page > 1:
                blob += "   " + self.text.make_chatcmd("<< Page %d" % (page - 1), self.get_chat_command(ql, search, page - 1))
            if offset + self.PAGE_SIZE < len(all_items):
                blob += "   Page " + str(page)
                blob += "   " + self.text.make_chatcmd("Page %d >>" % (page + 1), self.get_chat_command(ql, search, page + 1))
            blob += "\n"

            blob += self.format_items(items, ql)
            blob += "\nItem DB rips created using the %s tool." % self.text.make_chatcmd("Budabot Items Extractor", "/start https://github.com/Budabot/ItemsExtractor")

            return ChatBlob("Item Search Results (%d - %d of %d)" % (offset + 1, min(offset + self.PAGE_SIZE, len(all_items)), len(all_items)), blob)

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
        params = [name]
        sql = "SELECT * FROM aodb WHERE name LIKE ? "
        if ql:
            sql += " AND lowql <= ? AND highql >= ?"
            params.append(ql)
            params.append(ql)

        sql += " UNION SELECT * FROM aodb WHERE name <EXTENDED_LIKE=%d> ?" % len(params)
        params.append(name)

        if ql:
            sql += " AND lowql <= ? AND highql >= ?"
            params.append(ql)
            params.append(ql)

        sql += " ORDER BY name ASC, highql DESC"

        return self.db.query(sql, params, extended_like=True)

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

    def get_by_item_id(self, item_id, ql=None):
        if ql:
            return self.db.query_single("SELECT * FROM aodb WHERE (highid = ? OR lowid = ?) AND (highql = ? OR lowql = ?) ORDER BY highid = ?", [item_id, item_id, ql, ql, item_id])
        else:
            return self.db.query_single("SELECT * FROM aodb WHERE highid = ? OR lowid = ? ORDER BY highid = ?", [item_id, item_id, item_id])

    def find_by_name(self, name, ql=None):
        if ql:
            return self.db.query_single("SELECT * FROM aodb WHERE name = ? AND lowql <= ? AND highql >= ? ORDER BY highid DESC", [name, ql, ql])
        else:
            return self.db.query_single("SELECT * FROM aodb WHERE name = ? ORDER BY highql DESC, highid DESC", [name])

    def get_chat_command(self, ql, search, page):
        if ql:
            return "/tell <myname> items %d %s --page=%d" % (ql, search, page)
        else:
            return "/tell <myname> items %s --page=%d" % (search, page)
