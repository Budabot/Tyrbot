from core.decorators import instance
from core.access_manager import AccessManager
from core.aochat import server_packets
from core.budabot import Budabot
from core.character_manager import CharacterManager
import collections
import re


@instance()
class CommandManager:
    def __init__(self):
        self.db = None
        self.handlers = collections.defaultdict(list)
        self.commands = {}

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.access_manager: AccessManager = registry.get_instance("access_manager")
        self.bot: Budabot = registry.get_instance("budabot")
        self.character_manager: CharacterManager = registry.get_instance("character_manager")

    def start(self):
        self.bot.add_packet_handler(server_packets.PrivateMessage.id, self.handle_private_message)

    def register(self, handler, command, access_level, regex, sub_command=None):
        r = re.compile(regex, re.IGNORECASE)
        self.handlers[command].append({"handler": handler, "regex": r, "sub_command": sub_command or command})

        # TODO save to database
        self.commands[sub_command or command] = {
            "access_level": self.access_manager.get_access_level_by_label(access_level)
        }

    def process_command(self, message: str, channel: str, char_name, reply):
        command_str, command_args = self.get_command_parts(message)
        matches, handler = self.get_handler(command_str, command_args)
        if handler:
            # higher access levels have lower values
            if self.access_manager.get_access_level(char_name) <= self.commands[handler["sub_command"]]["access_level"]:
                handler["handler"](message, channel, char_name, reply, matches)
            else:
                reply("Error! Access denied.")
        else:
            reply("Error! Unknown command.")

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
