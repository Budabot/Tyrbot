from core.conn import Conn
from core.decorators import instance
from core.logger import Logger
from core.tyrbot import Tyrbot
from core.aochat import server_packets, client_packets


@instance()
class ExternalChannelController:
    def __init__(self):
        self.logger: Logger = Logger(__name__)

    def inject(self, registry):
        self.bot: Tyrbot = registry.get_instance("bot")
        self.character_service = registry.get_instance("character_service")
        self.command_service = registry.get_instance("command_service")
        self.setting_service = registry.get_instance("setting_service")
        self.ban_service = registry.get_instance("ban_service")

    def start(self):
        self.bot.register_packet_handler(server_packets.PrivateChannelInvited.id, self.handle_private_channel_invite)
        self.bot.register_packet_handler(server_packets.PrivateChannelMessage.id, self.handle_private_channel_message)

    def handle_private_channel_invite(self, conn: Conn, packet: server_packets.PrivateChannelInvited):
        if not conn.is_main:
            return

        channel_name = self.character_service.get_char_name(packet.private_channel_id)
        if self.ban_service.get_ban(packet.private_channel_id):
            self.logger.info("ignore private channel invite from banned char '%s'" % channel_name)
        else:
            conn.send_packet(client_packets.PrivateChannelJoin(packet.private_channel_id))
            self.logger.info("Joined private channel %s" % channel_name)

    def handle_private_channel_message(self, conn: Conn, packet: server_packets.PrivateChannelMessage):
        if not conn.is_main:
            return

        if packet.private_channel_id != conn.get_char_id():
            channel_name = self.character_service.get_char_name(packet.private_channel_id)
            char_name = self.character_service.get_char_name(packet.char_id)
            self.logger.log_chat(conn.id, "Private Channel(%s)" % channel_name, char_name, packet.message)

            if len(packet.message) < 2:
                return

            # ignore leading space
            message = packet.message.lstrip()

            if message.startswith(self.setting_service.get("symbol").get_value()):
                self.command_service.process_command(
                    self.command_service.trim_command_symbol(message),
                    self.command_service.PRIVATE_CHANNEL,
                    packet.char_id,
                    lambda msg: self.bot.send_private_channel_message(msg, private_channel_id=packet.private_channel_id, conn=conn),
                    conn)
