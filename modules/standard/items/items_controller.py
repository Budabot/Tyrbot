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

        count = 0
        reply(ChatBlob("Item Search Results (%d)" % count, str(ql) + " " + search))

    def get_by_item_id(self, item_id):
        return self.db.query_single("SELECT * FROM aodb WHERE highid = ? OR lowid = ? ORDER BY highid = ?", [item_id, item_id, item_id])

    def get_item_and_icon(self, item_id, ql=None):
        item = self.get_by_item_id(item_id)

        if not item:
            return None

        return self.text.make_image(item.icon) + "\n" + self.text.make_item(item.lowid, item.highid, ql or item.highql, item.name)
