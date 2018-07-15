from core.decorators import instance, command
from core.command_param_types import Any
import html


@instance()
class UtilController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.character_manager = registry.get_instance("character_manager")
        self.command_manager = registry.get_instance("command_manager")

    @command(command="checkaccess", params=[Any("character", is_optional=True)], access_level="all",
             description="Check access level for a character")
    def checkaccess_cmd(self, channel, sender, reply, args):
        char_name = args[0].capitalize() if args[0] else sender.name
        char_id = self.character_manager.resolve_char_to_id(char_name)

        if not char_id:
            reply("Could not find character <highlight>%s<end>." % char_name)
            return

        access_level = self.access_manager.get_access_level(char_id)
        reply("Access level for <highlight>%s<end> is <highlight>%s<end>." % (char_name, access_level["label"]))

    @command(command="macro", params=[Any("command 1|command 2|command 3 ...")], access_level="all",
             description="Execute multiple commands at once")
    def macro_cmd(self, channel, sender, reply, args):
        commands = args[0].split("|")
        for command_str in commands:
            self.command_manager.process_command(command_str, channel, sender.char_id, reply)

    @command(command="echo", params=[Any("message")], access_level="all",
             description="Echo back a message")
    def echo_cmd(self, channel, sender, reply, args):
        reply(html.escape(args[0]))

    @command(command="showcommand", params=[Any("character"), Any("message")], access_level="superadmin",
             description="Show command output to another character")
    def showcommand_cmd(self, channel, sender, reply, args):
        char_name = args[0].capitalize()
        command_str = args[1]

        char_id = self.character_manager.resolve_char_to_id(char_name)

        if not char_id:
            reply("Could not find <highlight>%s<end>." % char_name)
            return

        reply("Command <highlight>%s<end> output has been sent to <highlight>%s<end>." % (command_str, char_name))
        self.bot.send_private_message(char_id, "<highlight>%s<end> is showing you output for command <highlight>%s<end>:" % (sender.name, command_str))

        self.command_manager.process_command(command_str, channel, sender.char_id, lambda msg: self.bot.send_private_message(char_id, msg))
