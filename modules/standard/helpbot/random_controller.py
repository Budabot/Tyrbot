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
        self.character_manager = registry.get_instance("character_manager")
        self.command_alias_manager = registry.get_instance("command_alias_manager")

    def start(self):
        self.command_alias_manager.add_alias("verify", "roll verify")

    @command(command="random", params=[Any("items")], access_level="all",
             description="Randomly order a list of elements", extended_description="Enter a space-delimited list of items to randomize")
    def random_command(self, channel, sender, reply, args):
        options = args[0].split(" ")
        random.shuffle(options)
        reply(" ".join(options))

    @command(command="roll", params=[Int("start_value", is_optional=True), Int("end_value")], access_level="all",
             description="Roll a number between 1 and a number")
    def roll_command(self, channel, sender, reply, args):
        start = args[0] or 1
        end = args[1]

        if start > end:
            start, end = end, start

        result = random.randint(start, end)

        self.db.exec("INSERT INTO roll (char_id, min_value, max_value, result, created_at) VALUES (?, ?, ?, ?, ?)", [sender.char_id, start, end, result, int(time.time())])

        reply("Rolling between %d and %d: <highlight>%d<end>. /tell <myname> roll verify %d" % (start, end, result, self.db.last_insert_id()))

    @command(command="roll", params=[Const("verify"), Int("roll_id")], access_level="all",
             description="Verify a roll that happened")
    def roll_verify_command(self, channel, sender, reply, args):
        roll_id = args[1]

        row = self.db.query_single("SELECT * FROM roll WHERE id = ?", [roll_id])

        if not row:
            reply("Could not find roll with id <highlight>%d<end>." % roll_id)
        else:
            time_string = self.util.time_to_readable(int(time.time()) - row.created_at)
            name = self.character_manager.resolve_char_to_name(row.char_id)
            reply("Rolling between %d and %d: <highlight>%d<end>. %s ago for %s." % (row.min_value, row.max_value, row.result, time_string, name))
