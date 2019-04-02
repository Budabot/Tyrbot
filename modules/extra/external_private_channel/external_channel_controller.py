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

    def start(self):
        self.bot.add_packet_handler(server_packets.PrivateChannelInvited.id, self.handle_private_channel_invite)
        self.bot.add_packet_handler(server_packets.PrivateChannelMessage.id, self.handle_private_channel_message)

    def handle_private_channel_invite(self, packet: server_packets.PrivateChannelInvited):
        channel_name = self.character_service.get_char_name(packet.private_channel_id)
        self.bot.send_packet(client_packets.PrivateChannelJoin(packet.private_channel_id))
        self.logger.info("Joined private channel %s" % channel_name)

    def handle_private_channel_message(self, packet: server_packets.PrivateChannelMessage):
        if packet.private_channel_id != self.bot.char_id:
            channel_name = self.character_service.get_char_name(packet.private_channel_id)
            char_name = self.character_service.get_char_name(packet.char_id)
            self.logger.log_chat("Private Channel(%s)" % channel_name, char_name, packet.message)

            if len(packet.message) < 2:
                return

            # ignore leading space
            message = packet.message.lstrip()

            symbol = message[:1]
            command_str = message[1:]
            if symbol == self.setting_service.get("symbol").get_value():
                self.command_service.process_command(
                    command_str,
                    self.command_service.PRIVATE_CHANNEL,
                    packet.char_id,
                    lambda msg: self.bot.send_private_channel_message(msg, private_channel=packet.private_channel_id))
