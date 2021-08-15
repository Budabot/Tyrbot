from core.decorators import instance, command
from core.command_param_types import Any, Character
from core.standard_message import StandardMessage


@instance()
class RunasController:
    def inject(self, registry):
        self.command_service = registry.get_instance("command_service")
        self.access_service = registry.get_instance("access_service")
        self.getresp = registry.get_instance("translation_service").get_response

    @command(command="runas", params=[Character("character"), Any("command")], access_level="superadmin",
             description="Run a command as another character")
    def runas_cmd(self, request, char, command_str):
        if not char.char_id:
            return StandardMessage.char_not_found(char.name)
        elif not self.access_service.has_sufficient_access_level(request.sender.char_id, char.char_id):
            return self.getresp("module/system", "runas_fail", {"char": char.name})
        else:
            command_str = self.command_service.trim_command_symbol(command_str)
            self.command_service.process_command(command_str, request.channel, char.char_id, request.reply, request.conn)
