from core.decorators import instance, command
from core.command_manager import CommandManager


@instance()
class SystemController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")

    @command(command="shutdown", params=[], access_level="superadmin",
             description="Shutdown the bot")
    def shutdown_cmd(self, channel, sender, reply, args):
        msg = "The bot is shutting down..."
        self.bot.send_org_message(msg)
        self.bot.send_private_channel_message(msg)
        if channel not in [CommandManager.ORG_CHANNEL, CommandManager.PRIVATE_CHANNEL]:
            reply(msg)
        self.bot.shutdown()

    @command(command="restart", params=[], access_level="superadmin",
             description="Restart the bot")
    def restart_cmd(self, channel, sender, reply, args):
        msg = "The bot is restarting..."
        self.bot.send_org_message(msg)
        self.bot.send_private_channel_message(msg)
        if channel not in [CommandManager.ORG_CHANNEL, CommandManager.PRIVATE_CHANNEL]:
            reply(msg)
        self.bot.restart()
