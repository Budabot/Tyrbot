from core.decorators import instance, command
from core.command_param_types import Any
from core.db import DB
from core.text import Text


@instance()
class ChatController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")

    @command(command="loud", params=[Any("message")], access_level="all",
             description="Show a highly visible message", extended_description="This command is similar to <symbol>cmd in Budabot", aliases=["cmd"])
    def loud_command(self, request, message):
        return "\n<yellow>---------------------\n<red>%s<end>\n<yellow>---------------------" % message
