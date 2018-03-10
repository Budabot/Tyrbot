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

    def post_start(self):
        # process decorators
        for _, inst in Registry.get_all_instances().items():
            for name, method in inst.__class__.__dict__.items():
                if hasattr(method, "command"):
                    cmd_name, regex, access_level, sub_command = getattr(method, "command")
                    self.register(getattr(inst, name), cmd_name, regex, access_level, sub_command)

        # remove old sub_commands, add new sub_commands, load access levels from database
        data = self.db.query("SELECT sub_command, access_level FROM command_config")
        i = dict(zip(map((lambda x: x.sub_command), data), data))

        to_add = {k: v for k, v in self.temp_commands.items() if k not in i}
        for k, v in to_add.items():
            self.logger.debug("adding sub_command %s" % k)
            self.db.exec("INSERT INTO command_config (sub_command, access_level) VALUES (?, ?)", [k, v["access_level"]])

        to_remove = {k: v for k, v in i.items() if k not in self.temp_commands}
        for k, _ in to_remove.items():
            self.logger.debug("removing sub_command %s" % k)
            self.db.exec("DELETE FROM command_config WHERE sub_command = ?", [k])

        to_update = {k: v for k, v in i.items() if k in self.temp_commands and v["access_level"] != self.temp_commands[k]["access_level"]}
        for k, v in to_update.items():
            self.logger.debug("update access level for sub_command %s" % k)
            self.temp_commands[k]["access_level"] = v["access_level"]

        del self.temp_commands

    def register(self, handler, command, regex, access_level, sub_command):
        sub_cmd = sub_command or command
        r = re.compile(regex, re.IGNORECASE)
        self.handlers[command].append({"handler": handler, "regex": r, "sub_command": sub_cmd})

        self.temp_commands[sub_cmd] = {
            "access_level": access_level
        }

    def process_command(self, message: str, channel: str, char_name, reply):
        command_str, command_args = self.get_command_parts(message)
        matches, handler = self.get_handler(command_str, command_args)
        if handler:
            if self.has_sufficient_access_level_for_command(char_name, handler["sub_command"]):
                handler["handler"](message, channel, char_name, reply, matches)
            else:
                reply("Error! Access denied.")
        else:
            reply("Error! Unknown command.")

    def has_sufficient_access_level_for_command(self, char, sub_command):
        row = self.db.query_single("SELECT sub_command, access_level FROM command_config WHERE sub_command = ?", [sub_command])
        if row is None:
            raise Exception("Could not find sub_command '%s'" % sub_command)
        else:
            char_access_level = self.access_manager.get_access_level(char)
            cmd_access_level = self.access_manager.get_access_level_by_label(row.access_level)

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
                matches = handler["regex"].match(command_args)
                if matches:
                    return matches, handler
        return None, None

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
