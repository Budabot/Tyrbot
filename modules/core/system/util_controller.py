from core.chat_blob import ChatBlob
from core.decorators import instance, command
from core.command_param_types import Any, Character
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
        self.command_service = registry.get_instance("command_service")
        self.buddy_service = registry.get_instance("buddy_service")
        self.access_service = registry.get_instance("access_service")
        self.event_service = registry.get_instance("event_service")
        self.public_channel_service = registry.get_instance("public_channel_service")

    @command(command="checkaccess", params=[Character("character", is_optional=True)], access_level="all",
             description="Check access level for a character")
    def checkaccess_cmd(self, request, char):
        char = char or request.sender

        if not char.char_id:
            return "Could not find character <highlight>%s<end>." % char.name

        access_level = self.access_service.get_access_level(char.char_id)
        return "Access level for <highlight>%s<end> is <highlight>%s<end>." % (char.name, access_level["label"])

    @command(command="macro", params=[Any("command 1|command 2|command 3 ...")], access_level="all",
             description="Execute multiple commands at once")
    def macro_cmd(self, request, commands):
        commands = commands.split("|")
        for command_str in commands:
            self.command_service.process_command(command_str, request.channel, request.sender.char_id, request.reply)

    @command(command="echo", params=[Any("message")], access_level="all",
             description="Echo back a message")
    def echo_cmd(self, request, message):
        return html.escape(message)

    @command(command="showcommand", params=[Character("character"), Any("message")], access_level="superadmin",
             description="Show command output to another character")
    def showcommand_cmd(self, request, char, command_str):
        if not char.char_id:
            return "Could not find <highlight>%s<end>." % char.name

        self.bot.send_private_message(char.char_id, "<highlight>%s<end> is showing you output for command <highlight>%s<end>:" % (request.sender.name, command_str))

        self.command_service.process_command(command_str, request.channel, request.sender.char_id, lambda msg: self.bot.send_private_message(char.char_id, msg))

        return "Command <highlight>%s<end> output has been sent to <highlight>%s<end>." % (command_str, char.name)

    @command(command="system", params=[], access_level="admin",
             description="Show system information")
    def system_cmd(self, request):
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

        blob += "\n<pagebreak><header2>Public Channels<end>\n"
        for channel_id, name in self.public_channel_service.get_all_public_channels().items():
            blob += "%s - <highlight>%d<end>\n" % (name, channel_id)

        blob += "\n<pagebreak><header2>Event Types<end>\n"
        for event_type in self.event_service.get_event_types():
            blob += "%s\n" % event_type

        blob += "\n<pagebreak><header2>Access Levels<end>\n"
        for access_level in self.access_service.get_access_levels():
            blob += "%s (%d)\n" % (access_level["label"], access_level["level"])

        return ChatBlob("System Info", blob)

    @command(command="htmldecode", params=[Any("command")], access_level="all",
             description="Decode html entities from a command before passing to the bot for execution")
    def htmldecode_cmd(self, request, command_str):
        self.command_service.process_command(html.unescape(command_str), request.channel, request.sender.char_id, request.reply)
