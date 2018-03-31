from core.decorators import instance, command


@instance()
class SystemController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.bot = registry.get_instance("budabot")

    def start(self):
        pass

    @command(command="shutdown", params=[], access_level="superadmin",
             description="Shutdown the bot")
    def shutdown_cmd(self, channel, sender, reply, args):
        reply("Shutting down the bot...")
        self.bot.shutdown()

    @command(command="restart", params=[], access_level="superadmin",
             description="Restart the bot")
    def restart_cmd(self, channel, sender, reply, args):
        reply("Restarting down the bot...")
        self.bot.restart()
