from core.decorators import instance, command
from core.command_param_types import Const, Int, Any
from core.db import DB
from core.text import Text
import random
import time


@instance()
class QuoteController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")

    @command(command="quote", params=[], access_level="all",
             description="Show a random quote")
    def quote_command(self, channel, sender, reply, args):
        quote = self.get_quote_info()

        if quote:
            reply(quote)
        else:
            reply("There are no quotes to display.")

    @command(command="quote", params=[Int("quote_id")], access_level="all",
             description="Show a specific quote")
    def quote_view_command(self, channel, sender, reply, args):
        quote_id = args[0]

        quote = self.get_quote_info(quote_id)

        if quote:
            reply(quote)
        else:
            reply("Could not find quote with ID <highlight>%d<end>." % quote_id)

    @command(command="quote", params=[Const("add"), Any("quote")], access_level="all",
             description="Show a specific quote")
    def quote_add_command(self, channel, sender, reply, args):
        quote = args[1]

        if len(quote) > 4096:
            reply("Your quote must be less than 4096 characters.")
            return

        self.db.exec("INSERT INTO quote (char_id, created_at, content) VALUES (?, ?, ?)", [sender.char_id, int(time.time()), quote])

        reply("Your quote has been added successfully.")

    def get_quote_info(self, quote_id=None):
        stats = self.db.query_single("SELECT COUNT(1) AS count, MAX(id) AS max FROM quote")

        if stats.count == 0:
            return None

        if not quote_id:
            row = self.db.query_single("SELECT q.*, p.name FROM quote q LEFT JOIN player p ON q.char_id = p.char_id LIMIT 1 OFFSET ?", [random.randint(0, stats.count - 1)])
        else:
            row = self.db.query_single("SELECT q.*, p.name FROM quote q LEFT JOIN player p ON q.char_id = p.char_id WHERE id = ?", [quote_id])

        return "%d. %s" % (row.id, row.content)
