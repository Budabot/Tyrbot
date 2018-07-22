from core.decorators import instance, command
from core.command_param_types import Any


@instance()
class RunasController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.character_service = registry.get_instance("character_service")
        self.command_service = registry.get_instance("command_service")
        self.setting_service = registry.get_instance("setting_service")

    @command(command="runas", params=[Any("character"), Any("command")], access_level="superadmin",
             description="Run a command as another character")
    def shutdown_cmd(self, channel, sender, reply, args):
        char_name = args[0].capitalize()
        command_str = args[1]
        if command_str[0] == self.setting_service.get("symbol").get_value():
            command_str = command_str[1:]
        char_id = self.character_service.resolve_char_to_id(char_name)
        self.command_service.process_command(command_str, channel, char_id, reply)
