from core.conn import Conn
from core.dict_object import DictObject
from core.logger import Logger
from core.decorators import instance
from core.aochat import server_packets, client_packets


@instance()
class PrivateChannelService:
    PRIVATE_CHANNEL_MESSAGE_EVENT = "private_channel_message"
    JOINED_PRIVATE_CHANNEL_EVENT = "private_channel_joined"
    LEFT_PRIVATE_CHANNEL_EVENT = "private_channel_left"

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.event_service = registry.get_instance("event_service")
        self.character_service = registry.get_instance("character_service")
        self.access_service = registry.get_instance("access_service")

    def pre_start(self):
        self.event_service.register_event_type(self.JOINED_PRIVATE_CHANNEL_EVENT)
        self.event_service.register_event_type(self.LEFT_PRIVATE_CHANNEL_EVENT)
        self.event_service.register_event_type(self.PRIVATE_CHANNEL_MESSAGE_EVENT)

        self.bot.register_packet_handler(server_packets.PrivateChannelClientJoined.id, self.handle_private_channel_client_joined)
        self.bot.register_packet_handler(server_packets.PrivateChannelClientLeft.id, self.handle_private_channel_client_left)
        # priority must be above that of CommandService in order for relaying of commands to work correctly
        self.bot.register_packet_handler(server_packets.PrivateChannelMessage.id, self.handle_private_channel_message, priority=30)

        self.access_service.register_access_level("guest", 90, self.in_any_private_channel)

    def handle_private_channel_message(self, conn: Conn, packet: server_packets.PrivateChannelMessage):
        if not conn.is_main:
            return

        if packet.private_channel_id == conn.get_char_id():
            char_name = self.character_service.get_char_name(packet.char_id)
            self.logger.log_chat(conn.id, "Private Channel", char_name, packet.message)
            self.event_service.fire_event(self.PRIVATE_CHANNEL_MESSAGE_EVENT, DictObject({"char_id": packet.char_id,
                                                                                          "name": char_name,
                                                                                          "message": packet.message,
                                                                                          "conn": conn}))

    def handle_private_channel_client_joined(self, conn: Conn, packet: server_packets.PrivateChannelClientJoined):
        if not conn.is_main:
            return

        if packet.private_channel_id == conn.get_char_id():
            conn.private_channel[packet.char_id] = packet
            char_name = self.character_service.get_char_name(packet.char_id)
            self.logger.log_chat(conn.id, "Private Channel", None, f"{char_name} joined the channel.")
            self.event_service.fire_event(self.JOINED_PRIVATE_CHANNEL_EVENT, DictObject({"char_id": packet.char_id,
                                                                                         "name": char_name,
                                                                                         "conn": conn}))

    def handle_private_channel_client_left(self, conn: Conn, packet: server_packets.PrivateChannelClientLeft):
        if not conn.is_main:
            return

        if packet.private_channel_id == conn.get_char_id():
            del conn.private_channel[packet.char_id]
            char_name = self.character_service.get_char_name(packet.char_id)
            self.logger.log_chat(conn.id, "Private Channel", None, f"{char_name} left the channel.")
            self.event_service.fire_event(self.LEFT_PRIVATE_CHANNEL_EVENT, DictObject({"char_id": packet.char_id,
                                                                                       "name": char_name,
                                                                                       "conn": conn}))

    def invite(self, char_id, conn: Conn):
        if char_id != conn.get_char_id():
            conn.send_packet(client_packets.PrivateChannelInvite(char_id))

    def kick(self, char_id, conn: Conn):
        if char_id != conn.get_char_id():
            conn.send_packet(client_packets.PrivateChannelKick(char_id))

    def kickall(self, conn: Conn):
        conn.send_packet(client_packets.PrivateChannelKickAll())

    def in_any_private_channel(self, char_id):
        for _id, conn in self.bot.get_conns().items():
            if char_id in conn.private_channel:
                return True
        return False
