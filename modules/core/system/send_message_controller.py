from core.decorators import instance, command
from core.command_param_types import Any, Character


@instance()
class SendMessageController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.command_service = registry.get_instance("command_service")

    @command(command="sendtell", params=[Character("character"), Any("message")], access_level="superadmin",
             description="Send a tell to another character from the bot")
    def sendtell_cmd(self, request, char, message):
        if char.char_id:
            self.bot.send_private_message(char.char_id, message)
            return "Your message has been sent."
        else:
            return "Could not find character <highlight>%s<end>." % char.name
