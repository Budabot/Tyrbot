from core.decorators import instance, command
from core.command_param_types import Any


@instance()
class SystemController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.bot = registry.get_instance("budabot")
        self.access_manager = registry.get_instance("access_manager")

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

    @command(command="checkaccess", params=[Any("character")], access_level="all",
             description="Check access level for a character")
    def checkaccess_cmd(self, channel, sender, reply, args):
        char = args[1].capitalize()
        access_level = self.access_manager.get_access_level(char)
        reply("Access level for <highlight>%s<end> is <highlight>%s<end>." % (char, access_level["label"]))
