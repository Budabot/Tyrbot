from core.decorators import instance, command
from core.command_param_types import Any
import re


@instance()
class CalculatorController:
    def __init__(self):
        self.allow_chars_regex = re.compile("^[0123456789.,+\-*%()/ &|^~<>]+$")

    def inject(self, registry):
        self.discord_controller = registry.get_instance("discord_controller")

    def start(self):
        self.discord_controller.register_discord_command_handler(self.calc_discord_cmd, "calc", [Any("formula")])

    @command(command="calc", params=[Any("formula")], access_level="all",
             description="Perform a calculation")
    def calc_cmd(self, request, formula):
        if self.allow_chars_regex.match(formula):
            try:
                return "%s = %s" % (formula, round(eval(formula), 4))
            except SyntaxError:
                return "Invalid formula supplied."
        else:
            return "Invalid character detected."

    def calc_discord_cmd(self, reply, args):
        self.calc_cmd(None, None, reply, args)
