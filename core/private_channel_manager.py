from core.logger import Logger
from core.decorators import instance
from core.aochat import server_packets, client_packets


@instance()
class PrivateChannelManager:
    PRIVATE_CHANNEL_MESSAGE_EVENT = "private_channel_message"
    JOINED_PRIVATE_CHANNEL_EVENT = "private_channel_joined"
    LEFT_PRIVATE_CHANNEL_EVENT = "private_channel_left"

    def __init__(self):
        self.logger = Logger("private_channel_manager")
        self.private_channel_chars = {}

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.event_manager = registry.get_instance("event_manager")
        self.character_manager = registry.get_instance("character_manager")

    def pre_start(self):
        self.event_manager.register_event_type(self.JOINED_PRIVATE_CHANNEL_EVENT)
        self.event_manager.register_event_type(self.LEFT_PRIVATE_CHANNEL_EVENT)
        self.event_manager.register_event_type(self.PRIVATE_CHANNEL_MESSAGE_EVENT)
        self.bot.add_packet_handler(server_packets.PrivateChannelClientJoined.id, self.handle_private_channel_client_joined)
        self.bot.add_packet_handler(server_packets.PrivateChannelClientLeft.id, self.handle_private_channel_client_left)
        self.bot.add_packet_handler(server_packets.PrivateChannelMessage.id, self.handle_private_channel_message)

    def handle_private_channel_message(self, packet: server_packets.PrivateChannelMessage):
        if packet.private_channel_id == self.bot.char_id:
            char_name = self.character_manager.get_char_name(packet.char_id)
            self.logger.log_chat("Private Channel", char_name, packet.message)
            self.event_manager.fire_event(self.PRIVATE_CHANNEL_MESSAGE_EVENT, packet)

    def handle_private_channel_client_joined(self, packet: server_packets.PrivateChannelClientJoined):
        if packet.private_channel_id == self.bot.char_id:
            self.private_channel_chars[packet.char_id] = packet
            self.logger.log_chat("Private Channel", None, "%s joined the channel." % self.character_manager.get_char_name(packet.char_id))
            self.event_manager.fire_event(self.JOINED_PRIVATE_CHANNEL_EVENT, packet)

    def handle_private_channel_client_left(self, packet: server_packets.PrivateChannelClientLeft):
        if packet.private_channel_id == self.bot.char_id:
            del self.private_channel_chars[packet.char_id]
            self.logger.log_chat("Private Channel", None, "%s left the channel." % self.character_manager.get_char_name(packet.char_id))
            self.event_manager.fire_event(self.LEFT_PRIVATE_CHANNEL_EVENT, packet)

    def invite(self, char_id):
        if char_id != self.bot.char_id:
            self.bot.send_packet(client_packets.PrivateChannelInvite(char_id))

    def kick(self, char_id):
        if char_id != self.bot.char_id:
            self.bot.send_packet(client_packets.PrivateChannelKick(char_id))

    def kickall(self):
        self.bot.send_packet(client_packets.PrivateChannelKickAll())

    def in_private_channel(self, char_id):
        return char_id in self.private_channel_chars
