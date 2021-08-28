from core.decorators import instance, command
from core.command_param_types import Any, Int, Const, NamedParameters
from core.db import DB
import random
import time


@instance()
class RandomController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.character_service = registry.get_instance("character_service")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS roll (id INT PRIMARY KEY AUTO_INCREMENT, created_at INT NOT NULL, char_id INT NOT NULL, options VARCHAR(2048), result VARCHAR(255))")

        self.command_alias_service.add_alias("verify", "roll verify")
        self.command_alias_service.add_alias("lootorder", "random")

    @command(command="random", params=[Any("items"), NamedParameters(["separator"])], access_level="all",
             description="Randomly order a list of elements",
             extended_description="Default separator is a space.")
    def random_command(self, request, items, named_params):
        separator = named_params.separator if named_params.separator else " "
        items = items.split(separator)
        random.shuffle(items)
        return separator.join(items)

    @command(command="roll", params=[Const("verify"), Int("roll_id")], access_level="all",
             description="Verify a roll that happened")
    def roll_verify_command(self, request, _, roll_id):
        row = self.db.query_single("SELECT * FROM roll WHERE id = ?", [roll_id])
        if not row:
            return "Could not find roll with id <highlight>%d</highlight>." % roll_id
        else:
            time_string = self.util.time_to_readable(int(time.time()) - row.created_at)
            name = self.character_service.resolve_char_to_name(row.char_id)
            return "<highlight>%s</highlight> rolled by <highlight>%s</highlight> %s ago. Possible options: %s." % (
                row.result, name, time_string, row.options)

    @command(command="roll", params=[Int("start_value", is_optional=True), Int("end_value")], access_level="all",
             description="Roll a number between start_value and end_value number (inclusive)",
             extended_description="Start_value is assumed 1 if not provided.")
    def roll_number_command(self, request, start_value, end_value):
        start_value = start_value or 1
        if start_value > end_value:
            end = start_value
            start = end_value
        else:
            start = start_value
            end = end_value
        result = random.randint(start, end)
        options = "value between %d and %d" % (start, end)
        self.db.exec("INSERT INTO roll (created_at, char_id, options, result) VALUES (?, ?, ?, ?)",
                     [int(time.time()), request.sender.char_id, options, result])
        return "The roll is <highlight>%d</highlight> out of values between %d and %d. To verify do /tell <myname> verify %d" % (
            result, start, end, self.db.last_insert_id())

    # Keep this method at the bottom of file otherwise it will precede over all other commands
    @command(command="roll", params=[Any("items")], access_level="all",
             description="Roll a random value from a list of space-delimited values")
    def roll_text_variables_command(self, request, items):
        options = items.split(" ")
        result = random.choice(options)
        self.db.exec("INSERT INTO roll (created_at, char_id, options, result) VALUES (?, ?, ?, ?)",
                     [int(time.time()), request.sender.char_id, items, result])
        return "The roll is <highlight>%s</highlight> out of possible options: %s. To verify do /tell <myname> verify %d" % (
            result, items, self.db.last_insert_id())
