from core.decorators import instance
from core.access_manager import AccessManager
from core.aochat import server_packets
from core.character_manager import CharacterManager
from core.config.setting_manager import SettingManager
from core.registry import Registry
from core.logger import Logger
from core.budabot import Budabot
from core.chat_blob import ChatBlob
from pathlib import Path
import collections
import re


@instance()
class CommandManager:
    def __init__(self):
        self.handlers = collections.defaultdict(list)
        self.logger = Logger("command_manager")
        self.channels = ["private_message", "org_message", "private_channel_message"]

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.access_manager: AccessManager = registry.get_instance("access_manager")
        self.bot: Budabot = registry.get_instance("budabot")
        self.character_manager: CharacterManager = registry.get_instance("character_manager")
        self.setting_manager: SettingManager = registry.get_instance("setting_manager")
        self.command_alias_manager = registry.get_instance("command_alias_manager")

    def start(self):
        self.bot.add_packet_handler(server_packets.PrivateMessage.id, self.handle_private_message)
        self.bot.add_packet_handler(server_packets.PrivateChannelMessage.id, self.handle_private_channel_message)
        self.db.load_sql_file("./core/config/command_config.sql")
        self.db.exec("UPDATE command_config SET verified = 0")

    def post_start(self):
        # process decorators
        for _, inst in Registry.get_all_instances().items():
            for name, method in inst.__class__.__dict__.items():
                if hasattr(method, "command"):
                    cmd_name, regex, access_level, help_file, sub_command = getattr(method, "command")
                    handler = getattr(inst, name)
                    handler_name_parts = self.util.get_handler_name(handler).split(".")
                    module = handler_name_parts[1]
                    if help_file:
                        help_file = "./" + handler_name_parts[0] + "/" + handler_name_parts[1] + "/" + help_file
                    self.register(handler, cmd_name, regex, access_level, module, help_file, sub_command)

        self.db.exec("DELETE FROM command_config WHERE verified = 0")

    def register(self, handler, command, regex, access_level, module, help_file=None, sub_command=None):
        sub_command = sub_command or command
        command = command.lower()
        sub_command = sub_command.lower()
        access_level = access_level.lower()
        module = module.lower()

        if help_file is not None:
            if not Path(help_file).exists():
                self.logger.warning("Could not find help file '%s' for command '%s'" % (help_file, command))
        else:
            self.logger.warning("No help file specified for for command '%s'" % command)
            help_file = ""

        for channel in self.channels:
            row = self.db.query_single("SELECT access_level, help_file, module, enabled, verified "
                                       "FROM command_config "
                                       "WHERE command = ? AND sub_command = ? AND channel = ?",
                                       [command, sub_command, channel])

            if row is None:
                # add new command config
                self.db.exec(
                    "INSERT INTO command_config "
                    "(command, sub_command, access_level, channel, module, help_file, enabled, verified) "
                    "VALUES (?, ?, ?, ?, ?, ?, 1, 1)",
                    [command, sub_command, access_level, channel, module, help_file])
            elif row.verified:
                if row.access_level != access_level:
                    self.logger.warning(
                        "access_level different for different forms of command '%s' and sub_command '%s'" %
                        (command, sub_command))
                if row.help_file != help_file:
                    self.logger.warning(
                        "help_file different for different forms of command '%s' and sub_command '%s'" %
                        (command, sub_command))
                if row.module != module:
                    self.logger.warning(
                        "module different for different forms of command '%s' and sub_command '%s'" %
                        (command, sub_command))
            else:
                # mark command as verified
                self.db.exec("UPDATE command_config SET verified = 1, module = ?, help_file = ? "
                             "WHERE command = ? AND sub_command = ? AND channel = ?",
                             [module, help_file, command, sub_command, channel])

        # save reference to command handler
        r = re.compile(regex, re.IGNORECASE)
        self.handlers[self.get_command_key(command, sub_command)].append(
            {"regex": r, "callback": handler})

    def register_command_channel(self, channel):
        if channel in self.channels:
            self.logger.error("Could not register command channel '%s': command channel already registered"
                              % channel)
            return

        self.logger.debug("Registering command channel '%s'" % channel)
        self.channels.append(channel)

    def process_command(self, message: str, channel: str, char_name, reply):
        command_str, command_args = self.get_command_parts(message)

        # check for command alias
        command_str, command_args = self.command_alias_manager.check_for_alias(command_str, command_args)

        cmd_configs = self.get_command_configs(command_str, channel)
        if cmd_configs:
            cmd_config, matches, handler = self.get_matches(cmd_configs, command_args)
            if matches:
                if self.access_manager.check_access(char_name, cmd_config.access_level):
                    handler["callback"](message, channel, char_name, reply, matches)
                else:
                    reply("Error! Access denied.")
            else:
                # handlers were found, but no handler regex matched
                help_file = self.get_help_file(command_str, channel)
                if help_file:
                    reply(help_file)
                else:
                    reply("Error! Invalid syntax.")
        else:
            reply("Error! Unknown command.")

    def get_command_parts(self, message):
        parts = message.split(" ", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        else:
            return parts[0], ""

    def get_command_configs(self, command, channel):
        return self.db.query("SELECT command, sub_command, access_level FROM command_config "
                             "WHERE command = ? AND channel = ? AND enabled = 1",
                             [command, channel])

    def get_matches(self, cmd_configs, command_args):
        for row in cmd_configs:
            command_key = self.get_command_key(row.command, row.sub_command)
            handlers = self.handlers[command_key]
            for handler in handlers:
                matches = handler["regex"].match(command_args)
                if matches:
                    return row, matches, handler
        return None, None, None

    def get_help_file(self, command_str, channel):
        data = self.db.query("SELECT DISTINCT help_file FROM command_config "
                             "WHERE command = ? AND channel = ? AND enabled = 1",
                             [command_str, channel])

        def read_file(row):
            if row.help_file:
                with open(row.help_file) as f:
                    return f.read().strip()
            else:
                return ""

        content = "\n\n".join(map(read_file, data))
        if content:
            return ChatBlob("Help (" + command_str + ")", content)
        else:
            return None

    def get_command_key(self, command, sub_command):
        return command + ":" + sub_command

    def handle_private_message(self, packet: server_packets.PrivateMessage):
        if len(packet.message) < 1:
            return

        if packet.message[:1] == self.setting_manager.get("symbol"):
            command_str = packet.message[1:]
        else:
            command_str = packet.message

        self.process_command(
            command_str,
            "private_message",
            self.character_manager.get_char_name(packet.character_id),
            lambda msg: self.bot.send_private_message(packet.character_id, msg))

    def handle_private_channel_message(self, packet: server_packets.PrivateChannelMessage):
        if len(packet.message) < 2:
            return

        symbol = packet.message[:1]
        command_str = packet.message[1:]
        if symbol == self.setting_manager.get("symbol") and packet.character_id == self.bot.char_id:
            self.process_command(
                command_str,
                "private_channel_message",
                self.character_manager.get_char_name(packet.character_id),
                lambda msg: self.bot.send_private_channel_message(msg))
