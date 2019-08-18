from core.command_param_types import Const
from core.decorators import instance, command


@instance()
class QueueController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.getresp = registry.get_instance("translation_service").get_response

    def start(self):
        self.command_alias_service.add_alias("clearqueue", "queue clear")

    @command(command="queue", params=[Const("clear")], access_level="moderator",
             description="Clear the outgoing message queue")
    def queue_clear_cmd(self, request, _):
        num_messages = len(self.bot.packet_queue)
        self.bot.packet_queue.clear()
        return self.getresp("module/system", "clear_queue", {"count": num_messages})
