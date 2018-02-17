from core.decorators import instance
from core.access_manager import AccessManager
from core.aochat import server_packets
from core.budabot import Budabot
from core.character_manager import CharacterManager


@instance()
class CommandManager:
    def __init__(self):
        self.db = None
        self.commands = {}

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.access_manager: AccessManager = registry.get_instance("access_manager")
        self.bot: Budabot = registry.get_instance("budabot")
        self.character_manager: CharacterManager = registry.get_instance("character_manager")

    def start(self):
        self.bot.add_packet_handler(server_packets.PrivateMessage.id, self.handle_private_message)

    def register(self, handler, command, access_level):
        self.commands[command] = [{"handler": handler, "access_level": self.access_manager.get_access_level_by_level(access_level)}]

    def process_command(self, message: str, channel: str, char_name, reply):
        command_str, command_args = message.split(" ", 2)
        command = self.get_command(command_str)
        if command:
            if self.access_manager.get_access_level(char_name) >= command["access_level"]:
                command["handler"](message, channel, char_name, reply, command_args)
            else:
                reply("Error! Access denied.")
        else:
            reply("Error! Unknown command.")

    def get_command(self, command):
        return self.commands.get(command, None)

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

    # def register(self, module, handler, channels, command, access_levels, description, help_topic, default_status):
    #    for (channel, access_level) in zip(channels, access_levels):
    #        row = self.db.query_single("SELECT 1 FROM command WHERE cmd = ? AND channel = ?", command, channel)
    #        if row:
    #            sql = """
    #                UPDATE command_<myname> SET module = ?, handler = ?, description = ?, help = ?
    #                WHERE cmd = ? AND channel = ?
    #            """
    #            self.db.exec(sql, [module, handler, description, help_topic, command, channel])
    #        else:
    #            sql = """
    #                INSERT INTO command_<myname> (module, handler, cmd, channel, access_level, description, help, status)
    #                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    #            """
    #            self.db.exec(sql, [module, handler, command, channel, access_level, description, help_topic, default_status])
