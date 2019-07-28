from core.decorators import instance, command
from core.command_param_types import Any, Character


@instance()
class SendMessageController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.command_service = registry.get_instance("command_service")
        self.getresp = registry.get_instance("translation_service").get_response

    @command(command="sendtell", params=[Character("character"), Any("message")], access_level="superadmin",
             description="Send a tell to another character from the bot")
    def sendtell_cmd(self, request, char, message):
        if char.char_id:
            self.bot.send_private_message(char.char_id, message, add_color=False)
            return self.getresp("module/system", "msg_sent")
        else:
            return self.getresp("global", "char_not_found", {"char": char.name})
