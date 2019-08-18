from core.decorators import instance, command
from core.command_param_types import Any, Character


@instance()
class RunasController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.command_service = registry.get_instance("command_service")
        self.setting_service = registry.get_instance("setting_service")
        self.access_service = registry.get_instance("access_service")
        self.getresp = registry.get_instance("translation_service").get_response

    @command(command="runas", params=[Character("character"), Any("command")], access_level="superadmin",
             description="Run a command as another character")
    def shutdown_cmd(self, request, char, command_str):
        if command_str[0] == self.setting_service.get("symbol").get_value():
            command_str = command_str[1:]

        if not char.char_id:
            return self.getresp("global", "char_not_found", {"char": char.name})
        elif not self.access_service.has_sufficient_access_level(request.sender.char_id, char.char_id):
            return self.getresp("module/system", "runas_fail", {"char": char.name})
        else:
            self.command_service.process_command(command_str, request.channel, char.char_id, request.reply)
