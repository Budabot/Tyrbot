from core.decorators import instance, command
from core.command_param_types import Any, Int
from core.db import DB
from core.text import Text
import random


@instance()
class RandomController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")

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

        reply("Rolling between %d and %d: <highlight>%d<end>" % (start, end, random.randint(start, end)))
