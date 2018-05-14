from core.decorators import instance, command
from core.command_param_types import Any


@instance()
class CountdownController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.job_scheduler = registry.get_instance("job_scheduler")

    @command(command="countdown", params=[Any("message", is_optional=True)], access_level="all",
             description="Start a 5-second countdown")
    def whois_cmd(self, channel, sender, reply, args):
        message = args[0] if args[0] else "GO GO GO"
        message_format = "%s-------&gt; %s &lt;-------<end>"

        self.job_scheduler.delayed_job(self.show_countdown, 1, reply, message_format, "<red>", "5")
        self.job_scheduler.delayed_job(self.show_countdown, 2, reply, message_format, "<red>", "4")
        self.job_scheduler.delayed_job(self.show_countdown, 3, reply, message_format, "<orange>", "3")
        self.job_scheduler.delayed_job(self.show_countdown, 4, reply, message_format, "<orange>", "2")
        self.job_scheduler.delayed_job(self.show_countdown, 5, reply, message_format, "<orange>", "1")
        self.job_scheduler.delayed_job(self.show_countdown, 6, reply, message_format, "<green>", message)

    def show_countdown(self, timestamp, reply, message_format, color, message):
        reply(message_format % (color, message))
