from core.decorators import instance, command
from core.command_param_types import Any
from core.command_manager import CommandManager


@instance()
class SystemController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.access_manager = registry.get_instance("access_manager")
        self.command_manager = registry.get_instance("command_manager")

    def start(self):
        pass

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

    @command(command="checkaccess", params=[Any("character", is_optional=True)], access_level="all",
             description="Check access level for a character")
    def checkaccess_cmd(self, channel, sender, reply, args):
        char_name = args[0].capitalize() if args[0] else sender.name

        access_level = self.access_manager.get_access_level(char_name)
        if access_level:
            reply("Access level for <highlight>%s<end> is <highlight>%s<end>." % (char_name, access_level["label"]))
        else:
            reply("Could not find character <highlight>%s<end>." % char_name)

    @command(command="macro", params=[Any("command 1|command 2|command 3 ...")], access_level="all",
             description="Execute multiple commands at once")
    def macro_cmd(self, channel, sender, reply, args):
        commands = args[0].split("|")
        for command_str in commands:
            self.command_manager.process_command(command_str, channel, sender.char_id, reply)
