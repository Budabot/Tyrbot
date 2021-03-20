from core.decorators import instance, command
from core.command_param_types import Any, Character, Const


@instance()
class SendMessageController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.command_service = registry.get_instance("command_service")
        self.getresp = registry.get_instance("translation_service").get_response

    @command(command="send", params=[Const("tell"), Character("character"), Any("message")], access_level="superadmin",
             description="Send a message to a character from the bot")
    def send_tell_cmd(self, request, _, char, message):
        if char.char_id:
            self.bot.send_private_message(char.char_id, message, add_color=False, conn=request.conn)
            return self.getresp("module/system", "msg_sent")
        else:
            return self.getresp("global", "char_not_found", {"char": char.name})

    @command(command="send", params=[Const("org"), Any("message")], access_level="superadmin",
             description="Send a message to the org channel from the bot")
    def send_org_cmd(self, request, _, message):
        for _id, conn in self.bot.get_conns(lambda x: x.is_main):
            self.bot.send_org_message(message, add_color=False, conn=conn)
        return self.getresp("module/system", "msg_sent")

    @command(command="send", params=[Const("priv"), Any("message")], access_level="superadmin",
             description="Send a message to the private channel from the bot")
    def send_priv_cmd(self, request, _, message):
        self.bot.send_private_channel_message(message, add_color=False, conn=self.bot.get_primary_conn())
        return self.getresp("module/system", "msg_sent")
