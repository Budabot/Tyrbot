from core.chat_blob import ChatBlob
from core.decorators import instance, command
from core.command_param_types import Any
import time
import html
import os
import psutil
import sys
import platform


@instance()
class UtilController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.character_service = registry.get_instance("character_service")
        self.command_service = registry.get_instance("command_service")
        self.buddy_service = registry.get_instance("buddy_service")
        self.access_service = registry.get_instance("access_service")

    @command(command="checkaccess", params=[Any("character", is_optional=True)], access_level="all",
             description="Check access level for a character")
    def checkaccess_cmd(self, channel, sender, reply, char_name):
        char_name = char_name.capitalize() if char_name else sender.name
        char_id = self.character_service.resolve_char_to_id(char_name)

        if not char_id:
            return "Could not find character <highlight>%s<end>." % char_name

        access_level = self.access_service.get_access_level(char_id)
        return "Access level for <highlight>%s<end> is <highlight>%s<end>." % (char_name, access_level["label"])

    @command(command="macro", params=[Any("command 1|command 2|command 3 ...")], access_level="all",
             description="Execute multiple commands at once")
    def macro_cmd(self, channel, sender, reply, commands):
        commands = commands.split("|")
        for command_str in commands:
            self.command_service.process_command(command_str, channel, sender.char_id, reply)

    @command(command="echo", params=[Any("message")], access_level="all",
             description="Echo back a message")
    def echo_cmd(self, channel, sender, reply, message):
        return html.escape(message)

    @command(command="showcommand", params=[Any("character"), Any("message")], access_level="superadmin",
             description="Show command output to another character")
    def showcommand_cmd(self, channel, sender, reply, char_name, command_str):
        char_name = char_name.capitalize()

        char_id = self.character_service.resolve_char_to_id(char_name)

        if not char_id:
            return "Could not find <highlight>%s<end>." % char_name

        self.bot.send_private_message(char_id, "<highlight>%s<end> is showing you output for command <highlight>%s<end>:" % (sender.name, command_str))

        self.command_service.process_command(command_str, channel, sender.char_id, lambda msg: self.bot.send_private_message(char_id, msg))

        return "Command <highlight>%s<end> output has been sent to <highlight>%s<end>." % (command_str, char_name)

    @command(command="system", params=[], access_level="admin",
             description="Show system information")
    def system_cmd(self, channel, sender, reply):
        blob = ""
        blob += "Version: <highlight>Tyrbot %s<end>\n" % self.bot.version
        blob += "Name: <highlight><myname><end>\n"
        blob += "\n"
        blob += "OS: <highlight>%s %s<end>\n" % (platform.system(), platform.release())
        blob += "Python: <highlight>%d.%d.%d %s<end>\n" % (sys.version_info.major, sys.version_info.minor, sys.version_info.micro, sys.version_info.releaselevel)
        blob += "Database: <highlight>%s<end>\n" % self.db.type
        blob += "Memory Usage: <highlight>%s KB<end>\n" % self.util.format_number(psutil.Process(os.getpid()).memory_info().rss / 1024)
        blob += "\n"
        blob += "Superadmin: <highlight>%s<end>\n" % self.bot.superadmin
        blob += "Buddy List: <highlight>%d / %d<end>\n" % (len(self.buddy_service.buddy_list), self.buddy_service.buddy_list_size)
        blob += "Uptime: <highlight>%s<end>\n" % self.util.time_to_readable(int(time.time()) - self.bot.start_time, max_levels=None)

        return ChatBlob("System Info", blob)
