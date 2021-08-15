from core.command_param_types import Const, Any
from core.decorators import instance, command


@instance()
class QueueController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.command_service = registry.get_instance("command_service")

    def start(self):
        self.command_alias_service.add_alias("clearqueue", "queue clear")

    @command(command="queue", params=[Const("clear")], access_level="moderator",
             description="Clear the outgoing message queue")
    def queue_clear_cmd(self, request, _):
        num_messages = len(request.conn.packet_queue)
        request.conn.packet_queue.clear()
        return f"Cleared <highlight>{num_messages}</highlight> messages from the outgoing message queue."

    @command(command="massmsg", params=[Any("command")], access_level="moderator",
             description="Force the reply of the specified command to be sent via non-main bots")
    def massmsg_cmd(self, request, command_str):
        def reply(msg):
            self.bot.send_mass_message(request.sender.char_id, msg, conn=request.conn)

        self.command_service.process_command(command_str, request.channel, request.sender.char_id, reply, request.conn)
