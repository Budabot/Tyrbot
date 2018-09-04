from core.decorators import instance, command
from core.command_param_types import Any


@instance()
class CountdownController:
    def inject(self, registry):
        self.job_scheduler = registry.get_instance("job_scheduler")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("cd", "countdown")

    @command(command="countdown", params=[Any("message", is_optional=True)], access_level="all",
             description="Start a 5-second countdown")
    def countdown_cmd(self, request, message):
        message = message or "GO GO GO"
        message_format = "%s-------&gt; %s &lt;-------<end>"

        self.job_scheduler.delayed_job(self.show_countdown, 1, request.reply, message_format, "<red>", "5")
        self.job_scheduler.delayed_job(self.show_countdown, 2, request.reply, message_format, "<red>", "4")
        self.job_scheduler.delayed_job(self.show_countdown, 3, request.reply, message_format, "<orange>", "3")
        self.job_scheduler.delayed_job(self.show_countdown, 4, request.reply, message_format, "<orange>", "2")
        self.job_scheduler.delayed_job(self.show_countdown, 5, request.reply, message_format, "<orange>", "1")
        self.job_scheduler.delayed_job(self.show_countdown, 6, request.reply, message_format, "<green>", message)

    def show_countdown(self, timestamp, reply, message_format, color, message):
        reply(message_format % (color, message))
