import html
import os
import platform
import sys
import time

import psutil

from core.chat_blob import ChatBlob
from core.command_param_types import Any, Character, NamedFlagParameters
from core.decorators import instance, command
from core.standard_message import StandardMessage


@instance()
class UtilController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.text = registry.get_instance("text")
        self.command_service = registry.get_instance("command_service")
        self.buddy_service = registry.get_instance("buddy_service")
        self.access_service = registry.get_instance("access_service")
        self.event_service = registry.get_instance("event_service")
        self.public_channel_service = registry.get_instance("public_channel_service")

    def start(self):
        # init cpu percent calculation  see: https://psutil.readthedocs.io/en/latest/#psutil.Process.cpu_percent
        psutil.Process(os.getpid()).cpu_percent()

    @command(command="checkaccess", params=[Character("character")], access_level="moderator",
             description="Check access level for a character", sub_command="other")
    def checkaccess_other_cmd(self, request, char):
        if not char.char_id:
            return StandardMessage.char_not_found(char.name)

        return "Access level for <highlight>%s</highlight> is <highlight>%s</highlight> (%s)." % \
               (char.name, char.access_level["label"], self.access_service.get_single_access_level(char.char_id)["label"])

    @command(command="checkaccess", params=[], access_level="all",
             description="Check your access level")
    def checkaccess_cmd(self, request):
        char = request.sender

        return "Access level for <highlight>%s</highlight> is <highlight>%s</highlight> (%s)." % \
               (char.name, char.access_level["label"], self.access_service.get_single_access_level(char.char_id)["label"])

    @command(command="macro", params=[Any("command1|command2|command3...")], access_level="all",
             description="Execute multiple commands at once")
    def macro_cmd(self, request, commands):
        commands = commands.split("|")
        for command_str in commands:
            self.command_service.process_command(
                self.command_service.trim_command_symbol(command_str),
                request.channel,
                request.sender.char_id,
                request.reply,
                request.conn)

    @command(command="echo", params=[Any("message")], access_level="all",
             description="Echo back a message")
    def echo_cmd(self, request, message):
        return html.escape(message)

    @command(command="showcommand", params=[Character("character"), Any("message")], access_level="admin",
             description="Show command output to another character")
    def showcommand_cmd(self, request, char, command_str):
        if not char.char_id:
            return StandardMessage.char_not_found(char.name)

        self.bot.send_private_message(char.char_id,
                                      f"<highlight>{request.sender.name}</highlight> is showing you output for command <highlight>{command_str}</highlight>:",
                                      conn=request.conn)

        self.command_service.process_command(
            self.command_service.trim_command_symbol(command_str),
            request.channel,
            request.sender.char_id,
            lambda msg: self.bot.send_private_message(char.char_id, msg, conn=request.conn),
            request.conn)

        return f"Command <highlight>{command_str}</highlight> output has been sent to <highlight>{char.name}</highlight>."

    @command(command="system", params=[NamedFlagParameters(["show_all"])], access_level="superadmin",
             description="Show system information")
    def system_cmd(self, request, flag_params):
        mass_message_queue = "None"
        if self.bot.mass_message_queue:
            mass_message_queue = str(self.bot.mass_message_queue.qsize())

        python_version = str(sys.version_info.major) + "." + str(sys.version_info.minor) + "." + str(sys.version_info.micro) + "." + sys.version_info.releaselevel
        uptime = self.util.time_to_readable(int(time.time()) - self.bot.start_time, max_levels=None)
        
        process_info = psutil.Process(os.getpid())
        other_info = ""
        with process_info.oneshot():
            memory_usage = self.util.format_number(process_info.memory_info().rss / 1024)
            io_counters = process_info.io_counters()
            cpu_times = process_info.cpu_times()
            cpu_percent = process_info.cpu_percent()
            memory_info = process_info.memory_info()
            open_files = process_info.open_files()
            connections = process_info.connections()

        blob = f"Version: <highlight>Tyrbot {self.bot.version}</highlight>\n"
        blob += f"Name: <highlight><myname></highlight>\n\n"

        blob += f"OS: <highlight>{platform.system()} {platform.release()}</highlight>\n"
        blob += f"Python: <highlight>{python_version}</highlight>\n"
        blob += f"Database: <highlight>{self.db.type}</highlight>\n"
        blob += f"Memory Usage: <highlight>{memory_usage} KB</highlight>\n"

        if flag_params.show_all:
            blob += f"CPU Percent: <highlight>{cpu_percent}</highlight>\n"
            blob += f"IO Counters:\n"
            for k, v in io_counters._asdict().items():
                blob += f"   {k}: <highlight>{self.util.format_number(v)}</highlight>\n"
            blob += f"CPU Times:\n"
            for k, v in cpu_times._asdict().items():
                blob += f"   {k}: <highlight>{v}</highlight>\n"
            blob += f"Memory Info:\n"
            for k, v in memory_info._asdict().items():
                blob += f"    {k}: <highlight>{self.util.format_number(v)}</highlight>\n"
            blob += f"Open Files ({len(open_files)}):\n"
            for f in open_files:
                blob += f"    <highlight>{f.path}</highlight>\n"
            blob += f"Connections ({len(connections)}):\n"
            for c in connections:
                blob += f"    <highlight>{c}</highlight>\n"

        blob += "\n"

        blob += f"Superadmin: <highlight>{self.bot.superadmin}</highlight>\n"
        blob += f"Buddy List: <highlight>{self.buddy_service.get_buddy_list_size()}/{self.buddy_service.buddy_list_size}</highlight>\n"
        blob += f"Uptime: <highlight>{uptime}</highlight>\n"
        blob += f"Dimension: <highlight>{self.bot.dimension}</highlight>\n"
        blob += f"Mass Message Queue: <highlight>{mass_message_queue}</highlight>\n\n"

        blob += "<pagebreak><header2>Bots Connected</header2>\n"
        for _id, conn in self.bot.get_conns():
            blob += f"<highlight>{_id}</highlight> - {conn.char_name}({conn.char_id}) "
            if conn.org_id:
                blob += f"Org: {conn.get_org_name()}({conn.org_id})"
            if conn.is_main:
                blob += " <highlight>[main]</highlight>"
            blob += "\n"

            if flag_params.show_all:
                for channel_id, packet in conn.channels.items():
                    blob += f"{packet.args}\n"
                blob += "\n"

        if not flag_params.show_all:
            blob += "\n" + self.text.make_tellcmd("Show More Info", "system --show_all") + "\n"
        else:
            blob += "\n"

            blob += "<pagebreak><header2>Event Types</header2>\n"
            for event_type in self.event_service.get_event_types():
                blob += "%s\n" % event_type
            blob += "\n"

            blob += "<pagebreak><header2>Access Levels</header2>\n"
            for access_level in self.access_service.get_access_levels():
                blob += "%s (%d)\n" % (access_level["label"], access_level["level"])

        return ChatBlob("System Info", blob)

    @command(command="htmldecode", params=[Any("command")], access_level="all",
             description="Decode html entities from a command before passing to the bot for execution")
    def htmldecode_cmd(self, request, command_str):
        self.command_service.process_command(html.unescape(command_str), request.channel, request.sender.char_id, request.reply, request.conn)
