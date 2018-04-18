from core.decorators import instance, command
from core.chat_blob import ChatBlob
from core.command_param_types import Any


@instance()
class HelpController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.text = registry.get_instance("text")
        self.db = registry.get_instance("db")
        self.access_manager = registry.get_instance("access_manager")
        self.command_manager = registry.get_instance("command_manager")

    def start(self):
        pass

    @command(command="help", params=[], access_level="all",
             description="Show a list of commands to get help with")
    def help_list_cmd(self, channel, sender, reply, args):
        data = self.db.query("SELECT command, module, access_level FROM command_config "
                             "ORDER BY module ASC, command ASC")
        blob = ""
        current_group = ""
        current_module = ""
        current_command = ""
        for row in data:
            if not self.access_manager.check_access(sender.char_id, row.access_level):
                continue

            parts = row.module.split(".")
            group = parts[0]
            module = parts[1]
            if group != current_group:
                current_group = group
                blob += "\n\n<header2>" + current_group + "<end>"

            if module != current_module:
                current_module = module
                blob += "\n" + module + ":"

            if row.command != current_command:
                current_command = row.command
                blob += " " + self.text.make_chatcmd(row.command, "/tell <myname> help " + row.command)

        reply(ChatBlob("Help (main)", blob))

    @command(command="help", params=[Any("command")], access_level="all",
             description="Show help for a specific command")
    def help_detail_cmd(self, channel, sender, reply, args):
        help_topic = args[1].lower()
        help_text = self.command_manager.get_help_text(sender.char_id, help_topic, channel)
        if help_text:
            reply(self.command_manager.format_help_text(help_topic, help_text))
        else:
            reply("Could not find help on <highlight>" + help_topic + "<end>.")
