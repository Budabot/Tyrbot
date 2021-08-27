import os

from core.decorators import instance, command
from core.chat_blob import ChatBlob
from core.command_param_types import Any, NamedFlagParameters


@instance()
class HelpController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.text = registry.get_instance("text")
        self.db = registry.get_instance("db")
        self.access_service = registry.get_instance("access_service")
        self.command_service = registry.get_instance("command_service")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        self.command_alias_service.add_alias("version", "about")

    @command(command="about", params=[], access_level="all",
             description="Show information about the development of this bot")
    def about_cmd(self, request):
        with open(os.path.dirname(os.path.realpath(__file__)) + os.sep + "about.txt", mode="r", encoding="UTF-8") as f:
            return ChatBlob(f"About Tyrbot {self.bot.version}", f.read())

    @command(command="help", params=[], access_level="all",
             description="Show a list of commands to get help with")
    def help_list_cmd(self, request):
        data = self.db.query("SELECT command, module, access_level FROM command_config "
                             "WHERE enabled = 1 "
                             "ORDER BY module ASC, command ASC")
        blob = ""
        current_group = ""
        current_module = ""
        current_command = ""
        access_level = self.access_service.get_access_level(request.sender.char_id)
        for row in data:
            if access_level["level"] > self.access_service.get_access_level_by_label(row.access_level)["level"]:
                continue

            parts = row.module.split(".")
            group = parts[0]
            module = parts[1]
            if group != current_group:
                current_group = group
                blob += "\n\n<header2>" + current_group + "</header2>"

            if module != current_module:
                current_module = module
                blob += "\n" + module + ":"

            if row.command != current_command:
                current_command = row.command
                blob += " " + self.text.make_tellcmd(row.command, "help " + row.command)

        return ChatBlob("Help (main)", blob)

    @command(command="help", params=[Any("search"), NamedFlagParameters(["show_regex"])], access_level="all",
             description="Show help for a specific command",
             extended_description="Search param can be either a command name or a module name (eg. 'standard.online')")
    def help_detail_cmd(self, request, help_topic, named_params):
        help_topic = help_topic.lower()

        # check for alias
        alias = self.command_alias_service.check_for_alias(help_topic)
        if alias:
            help_topic = alias

        # check if help topic matches a command
        data = self.db.query("SELECT command, sub_command, access_level FROM command_config "
                             "WHERE command = ? AND channel = ? AND enabled = 1",
                             [help_topic, request.channel])

        help_text = self.command_service.format_help_text(data, request.sender.char_id, named_params.show_regex)
        if help_text:
            return self.command_service.format_help_text_blob(help_topic, help_text)

        # check if help topic matches a module
        data = self.db.query("SELECT command, sub_command, access_level FROM command_config "
                             "WHERE module = ? AND channel = ? AND enabled = 1",
                             [help_topic, request.channel])

        help_text = self.command_service.format_help_text(data, request.sender.char_id, named_params.show_regex)
        if help_text:
            return self.command_service.format_help_text_blob(help_topic, help_text)

        return f"Could not find help on <highlight>{help_topic}</highlight>."
