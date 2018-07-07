from core.decorators import instance, command
from core.command_param_types import Any
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
