from core.decorators import instance, command
from core.command_param_types import Any
import re


@instance()
class CalculatorController:
    def __init__(self):
        self.allow_chars_regex = re.compile(r"^[0123456789.+\-*%()/ &|^~<>]+$")

    def inject(self, registry):
        self.discord_controller = registry.get_instance("discord_controller")

    def start(self):
        self.discord_controller.register_discord_command_handler(self.calc_discord_cmd, "calc", [Any("formula")])

    @command(command="calc", params=[Any("formula")], access_level="all",
             description="Perform a calculation", extended_description="Supported operators:\n\n+ (addition)\n- (subtraction)\n* (multiplication)\n/ (division)\n"
                                                                       "% (modulus)\n** (exponent)\n// (floor/integer division)\n< (less than)\n> (greater than)\n"
                                                                       "() (parenthesis)\n& (binary AND)\n| (binary OR)\n^ (binary exclusive OR)\n~ (binary ones complement)\n"
                                                                       "<< (binary left shift)\n>> (binary right shift)")
    def calc_cmd(self, request, formula):
        # this may be problematic if this bot is running on a system with a different locale
        formula = formula.replace(",", ".")
        if self.allow_chars_regex.match(formula):
            try:
                return "%s = %s" % (formula, round(eval(formula), 4))
            except SyntaxError:
                return "Error! Invalid formula supplied."
        else:
            return "Error! Invalid character detected."

    def calc_discord_cmd(self, ctx, reply, args):
        reply(self.calc_cmd(None, *args))
