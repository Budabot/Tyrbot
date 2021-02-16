import html
import os
import platform
import sys
import time

import psutil

from core.chat_blob import ChatBlob
from core.command_param_types import Any, Character
from core.decorators import instance, command


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
        self.getresp = registry.get_instance("translation_service").get_response

    @command(command="checkaccess", params=[Character("character")], access_level="moderator",
             description="Check access level for a character", sub_command="other")
    def checkaccess_other_cmd(self, request, char):
        if not char.char_id:
            return self.getresp("global", "char_not_found", {"char": char.name})

        return self.getresp("module/system", "check_access",
                            {"char": char.name,
                             "rank_main": char.access_level["label"],
                             "rank_self": self.access_service.get_single_access_level(char.char_id)["label"]})

    @command(command="checkaccess", params=[], access_level="all",
             description="Check your access level")
    def checkaccess_cmd(self, request):
        char = request.sender

        return self.getresp("module/system", "check_access",
                            {"char": char.name,
                             "rank_main": char.access_level["label"],
                             "rank_self": self.access_service.get_single_access_level(char.char_id)["label"]})

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
            return self.getresp("global", "char_not_found", {"char": char.name})

        self.bot.send_private_message(char.char_id,
                                      self.getresp("module/system", "show_output_target", {"sender": request.sender.name, "cmd": command_str}),
                                      conn=request.conn)

        self.command_service.process_command(
            self.command_service.trim_command_symbol(command_str),
            request.channel,
            request.sender.char_id,
            lambda msg: self.bot.send_private_message(char.char_id, msg, conn=request.conn),
            request.conn)

        return self.getresp("module/system", "show_output_self",
                            {"target": char.name,
                             "cmd": command_str})

    @command(command="system", params=[], access_level="admin",
             description="Show system information")
    def system_cmd(self, request):
        mass_message_queue = "None"
        event_types = ""
        access_levels = ""
        bots_connected = ""

        for _id, conn in self.bot.conns.items():
            bots_connected += f"<highlight>{_id}</highlight> - {conn.char_name} ({conn.char_id})\n"
            if conn.is_main:
                bots_connected += f" └ Org: {conn.get_org_name()} ({conn.get_org_id()})\n"

                for channel_id, packet in conn.channels.items():
                    bots_connected += f" └ {packet.args}\n"

        for event_type in self.event_service.get_event_types():
            event_types += "%s\n" % event_type

        for access_level in self.access_service.get_access_levels():
            access_levels += "%s (%d)\n" % (access_level["label"], access_level["level"])

        if self.bot.mass_message_queue:
            mass_message_queue = str(self.bot.mass_message_queue.qsize())

        blob = self.getresp("module/system", "status_blob", {
            "bot_ver": self.bot.version,
            "os_ver": platform.system() + " " + platform.release(),
            "python_ver": str(sys.version_info.major) + "." + str(sys.version_info.minor) + "." + str(sys.version_info.micro) + "." + sys.version_info.releaselevel,
            "db_type": self.db.type,
            "mem_usage": self.util.format_number(psutil.Process(os.getpid()).memory_info().rss / 1024),
            "superadmin": self.bot.superadmin,
            "bl_used": self.buddy_service.get_buddy_list_size(),
            "bl_size": self.buddy_service.buddy_list_size,
            "uptime": self.util.time_to_readable(int(time.time()) - self.bot.start_time, max_levels=None),
            "dim": self.bot.dimension,
            "mass_message_queue": mass_message_queue,
            "bots_connected": bots_connected,
            "event_types": event_types,
            "access_levels": access_levels
        })

        return ChatBlob(self.getresp("module/system", "status_title"), blob)

    @command(command="htmldecode", params=[Any("command")], access_level="all",
             description="Decode html entities from a command before passing to the bot for execution")
    def htmldecode_cmd(self, request, command_str):
        self.command_service.process_command(html.unescape(command_str), request.channel, request.sender.char_id, request.reply, request.conn)
