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

    def pre_start(self):
        self.db.load_sql_file(self.module_dir + "/sql/" + "aodb.sql")

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
            return "Could not find item with ID <highlight>%d</highlight>." % item_id

    @command(command="items", params=[Int("ql", is_optional=True), Any("search"), NamedParameters(["page"])], access_level="all",
             description="Search for an item")
    def items_search_cmd(self, request, ql, search, named_params):
        page = int(named_params.page or "1")

        search = html.unescape(search)

        offset = (page - 1) * self.PAGE_SIZE

        all_items = self.find_items(search, ql)

        return self.format_items_response(ql, search, all_items, offset, page)

    def format_items_response(self, ql, search, all_items, offset, page_number):
        items = self.sort_items(search, all_items)[offset:offset + self.PAGE_SIZE]
        cnt = len(items)

        if cnt == 0:
            if ql:
                return "No QL <highlight>%d</highlight> items found matching <highlight>%s</highlight>." % (ql, search)
            else:
                return "No items found matching <highlight>%s</highlight>." % search
        elif cnt == 1:
            item = items[0]
            return self.format_single_item([item], ql)
        else:
            blob = ""
            # blob += "Version: <highlight>%s</highlight>\n" % "unknown"
            if ql:
                blob += "Search: <highlight>QL %d %s</highlight>\n" % (ql, search)
            else:
                blob += "Search: <highlight>%s</highlight>\n" % search
            blob += "\n"

            blob += self.text.get_paging_links(self.get_chat_command(ql, search), page_number, (offset + self.PAGE_SIZE) < len(all_items))
            blob += "\n\n"

            blob += self.format_items(items, ql)
            blob += "\nItem DB rips created using the %s tool." % self.text.make_chatcmd("Budabot Items Extractor", "/start https://github.com/Budabot/ItemsExtractor")

            return ChatBlob("Item Search Results (%d - %d of %d)" % (offset + 1, min(offset + self.PAGE_SIZE, len(all_items)), len(all_items)), blob)

    def format_items(self, items, ql=None):
        blob = ""
        for item_group in ItemIter(items):
            blob += "<pagebreak>"
            blob += self.text.make_image(item_group[0].icon) + "\n"
            blob += self.format_single_item(item_group, ql)
            blob += "\n\n"

        return blob

    def format_single_item(self, item_group, ql):
        msg = ""
        msg += item_group[0].name

        for item in reversed(item_group):
            if ql:
                if item.lowql != item.highql:
                    msg += " %s" % self.text.make_item(item.lowid, item.highid, ql, ql)
                    msg += " [%s - %s]" % (self.text.make_item(item.lowid, item.highid, item.lowql, item.lowql), self.text.make_item(item.lowid, item.highid, item.highql, item.highql))
                elif item.lowql == item.highql:
                    msg += " [%s]" % self.text.make_item(item.lowid, item.highid, item.highql, item.highql)
            elif item.lowql == item.highql:
                msg += " [%s]" % self.text.make_item(item.lowid, item.highid, item.highql, item.highql)
            else:
                msg += " [%s - %s]" % (self.text.make_item(item.lowid, item.highid, item.lowql, item.lowql), self.text.make_item(item.lowid, item.highid, item.highql, item.highql))

        return msg

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
            return self.db.query_single("SELECT * FROM aodb WHERE (highid = ? OR lowid = ?) AND (lowql <= ? AND highql >= ?) ORDER BY highid = ? DESC LIMIT 1", [item_id, item_id, ql, ql, item_id])
        else:
            return self.db.query_single("SELECT * FROM aodb WHERE highid = ? OR lowid = ? ORDER BY highid = ? DESC LIMIT 1", [item_id, item_id, item_id])

    def find_by_name(self, name, ql=None):
        if ql:
            return self.db.query_single("SELECT * FROM aodb WHERE name = ? AND lowql <= ? AND highql >= ? ORDER BY highid DESC LIMIT 1", [name, ql, ql])
        else:
            return self.db.query_single("SELECT * FROM aodb WHERE name = ? ORDER BY highql DESC, highid DESC LIMIT 1", [name])

    def get_chat_command(self, ql, search):
        if ql:
            return "items %d %s" % (ql, search)
        else:
            return "items %s" % search


class ItemIter:

    """Iterator that groups items with the same name and icon together."""

    def __init__(self, items):
        self.items = items
        self.current_index = 0

    def __iter__(self):
        return self

    def __next__(self):
        num_items = len(self.items)
        if self.current_index >= num_items:
            raise StopIteration
        else:
            grouped = []

            item = self.items[self.current_index]
            self.current_index += 1
            grouped.append(item)
            current_item = item
            while self.current_index < num_items:
                item = self.items[self.current_index]
                if item.name != current_item.name or item.icon != current_item.icon or item.highql == current_item.highql:
                    break
                current_item = item
                grouped.append(item)
                self.current_index += 1

            return grouped
