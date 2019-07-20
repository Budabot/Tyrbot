import os

import hjson

from core.decorators import instance, command
from core.chat_blob import ChatBlob
from core.command_param_types import Any, NamedParameters
from core.translation_service import TranslationService


@instance()
class HelpController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.text = registry.get_instance("text")
        self.db = registry.get_instance("db")
        self.access_service = registry.get_instance("access_service")
        self.command_service = registry.get_instance("command_service")
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.ts: TranslationService = registry.get_instance("translation_service")
        self.getresp = self.ts.get_response

    def start(self):
        self.ts.register_translation("module/help", self.load_help_msg)
        self.command_alias_service.add_alias("version", "about")

    def load_help_msg(self):
        with open("modules/core/help/help.msg", mode="r", encoding="UTF-8") as f:
            return hjson.load(f)

    @command(command="about", params=[], access_level="all",
             description="Show information about the development of this bot")
    def about_cmd(self, request):
        blob = self.getresp("module/help", "about_head")
        blob += self.getresp("module/help", "about_body")
        blob += self.getresp("module/help", "about_special_ones")
        blob += self.getresp("module/help", "about_improvers")
        blob += self.getresp("module/help", "about_bottom")
        return ChatBlob(self.getresp("module/help", "blob_title", {"ver": self.bot.version}), blob)

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

    @command(command="help", params=[Any("command"), NamedParameters(["show_regex"])], access_level="all",
             description="Show help for a specific command")
    def help_detail_cmd(self, request, help_topic, named_params):
        help_topic = help_topic.lower()

        # check for alias
        alias = self.command_alias_service.check_for_alias(help_topic)
        if alias:
            help_topic = alias

        show_regex = named_params.show_regex and named_params.show_regex.lower() == "true"

        help_text = self.command_service.get_help_text(request.sender.char_id, help_topic, request.channel, show_regex)
        if help_text:
            return self.command_service.format_help_text(help_topic, help_text)
        else:
            return self.getresp("module/help", "no_help", {"topic": help_topic})
