from core.chat_blob import ChatBlob
from core.decorators import instance, command
from core.command_param_types import Const, Int, Any, Options
from core.db import DB
from core.text import Text
import random
import time


@instance()
class QuoteController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.util = registry.get_instance("util")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS quote (id INT PRIMARY KEY AUTO_INCREMENT, char_id INT NOT NULL, created_at INT NOT NULL, content VARCHAR(4096) NOT NULL)")

    @command(command="quote", params=[], access_level="guest",
             description="Show a random quote")
    def quote_command(self, request):
        quote = self.get_random_quote()

        if quote:
            return self.format_quote(quote, request.conn)
        else:
            return "There are no quotes to display."

    @command(command="quote", params=[Int("quote_id")], access_level="guest",
             description="Show a specific quote")
    def quote_view_command(self, request, quote_id):
        quote = self.get_quote_info(quote_id)

        if quote:
            return self.format_quote(quote, request.conn)
        else:
            return "Quote with ID <highlight>%d</highlight> does not exist." % quote_id

    @command(command="quote", params=[Const("add"), Any("quote")], access_level="guest",
             description="Show a specific quote")
    def quote_add_command(self, request, _, quote):
        if len(quote) > 4096:
            return "Your quote must be less than 4096 characters."

        next_id = self.db.query_single("SELECT (COALESCE(MAX(id), 0) + 1) AS next_id FROM quote").next_id
        self.db.exec("INSERT INTO quote (id, char_id, created_at, content) VALUES (?, ?, ?, ?)", [next_id, request.sender.char_id, int(time.time()), quote])

        return f"Quote with ID <highlight>{next_id}</highlight> has been added successfully."

    @command(command="quote", params=[Options(["rem", "remove"]), Int("quote_id")], access_level="moderator",
             description="Remove a quote", sub_command="remove")
    def quote_remove_command(self, request, _, quote_id):
        num_rows = self.db.exec("DELETE FROM quote WHERE id = ?", [quote_id])

        if num_rows:
            return f"Quote with ID <highlight>{quote_id}</highlight> has been removed successfully."
        else:
            return "Quote with ID <highlight>%d</highlight> does not exist." % quote_id

    @command(command="quote", params=[Const("search"), Any("search_params")], access_level="guest",
             description="Search for a quote")
    def quote_search_command(self, request, _, search_params):
        sql = "SELECT q.*, p.name FROM quote q LEFT JOIN player p ON q.char_id = p.char_id " \
              "WHERE q.content <EXTENDED_LIKE=0> ? OR p.name LIKE ? " \
              "ORDER BY q.id ASC"
        data = self.db.query(sql, [search_params, search_params], extended_like=True)

        blob = ""
        for row in data:
            blob += self.text.make_tellcmd(row.id, f"quote {row.id}")
            blob += " "
            blob += row.content
            blob += "\n\n"

        return ChatBlob("Quote Search Results (%d)" % len(data), blob)

    def get_random_quote(self):
        quotes = self.db.query("SELECT q.*, p.name FROM quote q LEFT JOIN player p ON q.char_id = p.char_id ORDER BY q.id ASC")
        if quotes:
            return random.choice(quotes)
        else:
            return None

    def get_quote_info(self, quote_id):
        return self.db.query_single("SELECT q.*, p.name FROM quote q LEFT JOIN player p ON q.char_id = p.char_id WHERE q.id = ?", [quote_id])

    def format_quote(self, quote, conn):
        blob = f"ID: <highlight>{quote.id}</highlight>\n"
        blob += f"Created By: <highlight>{quote.name or quote.char_id}</highlight>\n"
        blob += f"Created At: <highlight>{self.util.format_datetime(quote.created_at)}</highlight>\n\n"
        blob += quote.content

        chat_blob = ChatBlob("More Info", blob)
        more_info_link = self.text.paginate(chat_blob, conn)[0]
        return "%d. %s %s" % (quote.id, quote.content, more_info_link)
