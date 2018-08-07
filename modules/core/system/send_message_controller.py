from core.decorators import instance, command
from core.command_param_types import Any, Character


@instance()
class SendMessageController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.character_service = registry.get_instance("character_service")
        self.command_service = registry.get_instance("command_service")

    @command(command="sendtell", params=[Character("character"), Any("message")], access_level="superadmin",
             description="Send a tell to another character from the bot")
    def sendtell_cmd(self, request, char_name, message):
        char_id = self.character_service.resolve_char_to_id(char_name)
        if char_id:
            self.bot.send_private_message(char_id, message)
            return "Your message has been sent."
        else:
            return "Could not find character <highlight>%s<end>." % char_name
