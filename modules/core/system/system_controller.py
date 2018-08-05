from core.decorators import instance, command, event, setting
from core.command_service import CommandService
from core.setting_types import BooleanSettingType


@instance()
class SystemController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")

    @setting(name="expected_shutdown", value="true", description="Helps bot to determine if last shutdown was expected or due to a problem")
    def expected_shutdown(self):
        return BooleanSettingType()

    @command(command="shutdown", params=[], access_level="superadmin",
             description="Shutdown the bot")
    def shutdown_cmd(self, channel, sender, reply, args):
        msg = "The bot is shutting down..."
        self.bot.send_org_message(msg)
        self.bot.send_private_channel_message(msg)

        # set expected flag
        self.expected_shutdown().set_value(True)

        if channel not in [CommandService.ORG_CHANNEL, CommandService.PRIVATE_CHANNEL]:
            reply(msg)

        self.bot.shutdown()

    @command(command="restart", params=[], access_level="superadmin",
             description="Restart the bot")
    def restart_cmd(self, channel, sender, reply, args):
        msg = "The bot is restarting..."
        self.bot.send_org_message(msg)
        self.bot.send_private_channel_message(msg)

        # set expected flag
        self.expected_shutdown().set_value(True)

        if channel not in [CommandService.ORG_CHANNEL, CommandService.PRIVATE_CHANNEL]:
            reply(msg)

        self.bot.restart()

    @event(event_type="connect", description="Notify superadmin that bot has come online")
    def connect_event(self, event_type, event_data):
        if self.expected_shutdown().get_value():
            msg = "<myname> is now <green>online<end>."
        else:
            msg = "<myname> is now <green>online<end> but may have shut down or restarted unexpectedly. Please check the logs."

        self.bot.send_private_message(self.bot.superadmin, msg)
        self.bot.send_org_message(msg)
        self.bot.send_private_channel_message(msg)

        self.expected_shutdown().set_value(False)
