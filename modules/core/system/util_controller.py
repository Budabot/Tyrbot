from core.decorators import instance, command
from core.command_param_types import Any
import html


@instance()
class UtilController:
    def inject(self, registry):
        pass

    @command(command="echo", params=[Any("message")], access_level="superadmin",
             description="Echoes back what was sent")
    def echo_cmd(self, channel, sender, reply, args):
        reply(html.escape(args[0]))
