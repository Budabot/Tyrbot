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
        self.access_service = registry.get_instance("access_service")
        self.command_service = registry.get_instance("command_service")
        self.command_alias_service = registry.get_instance("command_alias_service")

    def start(self):
        pass

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
                blob += "\n\n<header2>" + current_group + "<end>"

            if module != current_module:
                current_module = module
                blob += "\n" + module + ":"

            if row.command != current_command:
                current_command = row.command
                blob += " " + self.text.make_chatcmd(row.command, "/tell <myname> help " + row.command)

        return ChatBlob("Help (main)", blob)

    @command(command="help", params=[Any("command")], access_level="all",
             description="Show help for a specific command")
    def help_detail_cmd(self, request, help_topic):
        help_topic = help_topic.lower()

        # check for alias
        alias = self.command_alias_service.check_for_alias(help_topic)
        if alias:
            help_topic = alias

        help_text = self.command_service.get_help_text(request.sender.char_id, help_topic, request.channel)
        if help_text:
            return self.command_service.format_help_text(help_topic, help_text)
        else:
            return "Could not find help on <highlight>" + help_topic + "<end>."
