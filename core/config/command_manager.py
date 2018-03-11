from core.decorators import instance
from core.access_manager import AccessManager
from core.aochat import server_packets
from core.budabot import Budabot
from core.character_manager import CharacterManager
from core.registry import Registry
from core.logger import Logger
import collections
import re


@instance()
class CommandManager:
    def __init__(self):
        self.db = None
        self.handlers = collections.defaultdict(list)
        self.temp_commands = {}
        self.logger = Logger("command_manager")

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.access_manager: AccessManager = registry.get_instance("access_manager")
        self.bot: Budabot = registry.get_instance("budabot")
        self.character_manager: CharacterManager = registry.get_instance("character_manager")

    def start(self):
        self.bot.add_packet_handler(server_packets.PrivateMessage.id, self.handle_private_message)
        self.db.load_sql_file("./core/config/command_config.sql")
        self.db.exec("UPDATE command_config SET verified = 0")

    def post_start(self):
        # process decorators
        for _, inst in Registry.get_all_instances().items():
            for name, method in inst.__class__.__dict__.items():
                if hasattr(method, "command"):
                    cmd_name, regex, access_level, sub_command = getattr(method, "command")
                    self.register(getattr(inst, name), cmd_name, regex, access_level, sub_command)

        self.db.exec("DELETE FROM command_config WHERE verified = 0")

    def register(self, handler, command, regex, access_level, sub_command=None):
        sub_command = sub_command or command

        row = self.db.query_single("SELECT sub_command, access_level, enabled, verified "
                                   "FROM command_config WHERE sub_command = ?",
                                   [sub_command])

        if row is None:
            # add new command config
            self.db.exec(
                "INSERT INTO command_config (sub_command, access_level, enabled, verified) VALUES (?, ?, ?, ?)",
                [sub_command, access_level, 1, 1])
        else:
            # mark command as verified
            self.db.exec("UPDATE command_config SET verified = ? WHERE sub_command = ?", [1, sub_command])

        # load command handler
        r = re.compile(regex, re.IGNORECASE)
        self.handlers[command].append({"handler": handler, "regex": r, "sub_command": sub_command})

    def process_command(self, message: str, channel: str, char_name, reply):
        command_str, command_args = self.get_command_parts(message)
        matches, handler, cmd_config = self.get_handler(command_str, command_args)
        if handler:
            if self.has_sufficient_access_level_for_command(char_name, cmd_config):
                handler["handler"](message, channel, char_name, reply, matches)
            else:
                reply("Error! Access denied.")
        else:
            reply("Error! Unknown command.")

    def has_sufficient_access_level_for_command(self, char, cmd_config):
        char_access_level = self.access_manager.get_access_level(char)
        cmd_access_level = self.access_manager.get_access_level_by_label(cmd_config.access_level)

        # higher access levels have lower values
        return char_access_level <= cmd_access_level

    def get_command_parts(self, message):
        parts = message.split(" ", 2)
        if len(parts) == 2:
            return parts[0], parts[1]
        else:
            return parts[0], ""

    def get_handler(self, command, command_args):
        handlers = self.handlers.get(command, None)
        if handlers:
            for handler in handlers:
                sub_command = handler["sub_command"]
                matches = handler["regex"].match(command_args)
                if matches:
                    row = self.db.query_single("SELECT sub_command, access_level, enabled FROM command_config WHERE sub_command = ?",
                                               [sub_command])
                    if row is None:
                        raise Exception("Could not find sub_command '%s'" % sub_command)
                    elif row.enabled == 1:
                        return matches, handler, row

        return None, None, None

    def handle_private_message(self, packet: server_packets.PrivateMessage):
        if len(packet.message) < 2:
            return

        symbol = packet.message[:1]
        command_str = packet.message[1:]
        if symbol == "!":
            self.process_command(
                command_str,
                "private_message",
                self.character_manager.get_char_name(packet.character_id),
                lambda msg: self.bot.send_private_message(packet.character_id, msg))
