from core.decorators import instance, command
from core.command_param_types import Any, Int, Const
from core.db import DB
from core.text import Text
import random
import time


@instance()
class RandomController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.character_service = registry.get_instance("character_service")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("verify", "roll verify")

    @command(command="random", params=[Any("items")], access_level="all",
             description="Randomly order a list of elements", extended_description="Enter a space-delimited list of items to randomize")
    def random_command(self, request, items):
        items = items.split(" ")
        random.shuffle(items)
        return " ".join(items)

    @command(command="roll", params=[Int("start_value", is_optional=True), Int("end_value")], access_level="all",
             description="Roll a number between 1 and a number")
    def roll_command(self, request, start_value, end_value):
        start_value = start_value or 1

        if start_value > end_value:
            start_value, end = end_value, start_value

        result = random.randint(start_value, end_value)

        self.db.exec("INSERT INTO roll (char_id, min_value, max_value, result, created_at) VALUES (?, ?, ?, ?, ?)", [sender.char_id, start_value, end_value, result, int(time.time())])

        return "Rolling between %d and %d: <highlight>%d<end>. /tell <myname> roll verify %d" % (start_value, end_value, result, self.db.last_insert_id())

    @command(command="roll", params=[Const("verify"), Int("roll_id")], access_level="all",
             description="Verify a roll that happened")
    def roll_verify_command(self, request, _, roll_id):
        row = self.db.query_single("SELECT * FROM roll WHERE id = ?", [roll_id])

        if not row:
            return "Could not find roll with id <highlight>%d<end>." % roll_id
        else:
            time_string = self.util.time_to_readable(int(time.time()) - row.created_at)
            name = self.character_service.resolve_char_to_name(row.char_id)
            return "Rolling between %d and %d: <highlight>%d<end>. %s ago for %s." % (row.min_value, row.max_value, row.result, time_string, name)
