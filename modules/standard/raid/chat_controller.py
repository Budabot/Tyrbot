from core.decorators import instance, command
from core.command_param_types import Any


@instance()
class ChatController:
    def inject(self, registry):
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("cmd", "shout")

    @command(command="shout", params=[Any("message")], access_level="all",
             description="Show a highly visible message",
             extended_description="This command is similar to <symbol>cmd in Budabot")
    def shout_command(self, _, message):
        return "\n<yellow>---------------------</yellow>\n<red>%s</red>\n<yellow>---------------------</yellow>" % message
