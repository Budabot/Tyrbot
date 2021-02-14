from core.conn import Conn
from core.decorators import instance
from core.aochat import server_packets
from core.logger import Logger


class ConnPublicChannelInfo:
    def __init__(self):
        self.channels = {}
        self.org_channel_id = None
        self.org_id = None
        self.org_name = None


@instance()
class PublicChannelService:
    ORG_CHANNEL_MESSAGE_EVENT = "org_channel_message"
    ORG_MSG_EVENT = "org_msg"

    ORG_MSG_CHANNEL_ID = 42949672961

    def __init__(self):
        self.logger = Logger(__name__)
        self.conns = {}
        self.id_to_name = {}

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.event_service = registry.get_instance("event_service")
        self.character_service = registry.get_instance("character_service")
        self.setting_service = registry.get_instance("setting_service")

    def pre_start(self):
        self.bot.register_packet_handler(server_packets.LoginOK.id, self.handle_login_ok)
        self.bot.register_packet_handler(server_packets.PublicChannelJoined.id, self.add)
        self.bot.register_packet_handler(server_packets.PublicChannelLeft.id, self.remove)
        # priority must be above that of CommandService in order for relaying of commands to work correctly
        self.bot.register_packet_handler(server_packets.PublicChannelMessage.id, self.public_channel_message, priority=30)
        self.event_service.register_event_type(self.ORG_CHANNEL_MESSAGE_EVENT)
        self.event_service.register_event_type(self.ORG_MSG_EVENT)

    def handle_login_ok(self, conn: Conn, packet):
        if not conn.is_main:
            return

        self.conns[conn.id] = ConnPublicChannelInfo()
        # TODO load org name and org id from table

    def get_channel_name(self, channel_id):
        return self.id_to_name.get(channel_id, None)

    def add(self, conn: Conn, packet: server_packets.PublicChannelJoined):
        if not conn.is_main:
            return

        conn_info = self.conns[conn.id]
        conn_info.channels[packet.channel_id] = packet
        if not conn_info.org_id and self.is_org_channel_id(packet.channel_id):
            conn_info.org_channel_id = packet.channel_id
            conn_info.org_id = 0x00ffffffff & packet.channel_id

            if packet.name != "Clan (name unknown)":
                # TODO store in table
                # self.setting_service.get("org_name").set_value(packet.name)
                conn_info.org_name = packet.name

            self.logger.info(f"Org info for '{conn.id}': {conn_info.org_name} ({conn_info.org_id})")

    def remove(self, conn: Conn, packet: server_packets.PublicChannelLeft):
        if not conn.is_main:
            return

        del self.conns[conn.id].channels[packet.channel_id]

    def public_channel_message(self, conn: Conn, packet: server_packets.PublicChannelMessage):
        if not conn.is_main:
            return

        if self.is_org_channel_id(packet.channel_id):
            char_name = self.character_service.get_char_name(packet.char_id)
            if packet.extended_message:
                message = packet.extended_message.get_message()
            else:
                message = packet.message
            self.logger.log_chat(conn.id, "Org Channel", char_name, message)
            self.event_service.fire_event(self.ORG_CHANNEL_MESSAGE_EVENT, packet)
        elif packet.channel_id == self.ORG_MSG_CHANNEL_ID:
            char_name = self.character_service.get_char_name(packet.char_id)
            if packet.extended_message:
                message = packet.extended_message.get_message()
            else:
                message = packet.message
            self.logger.log_chat(conn.id, "Org Msg", char_name, message)
            self.event_service.fire_event(self.ORG_MSG_EVENT, packet)

    def is_org_channel_id(self, channel_id):
        return channel_id >> 32 == 3

    def get_org_id(self):
        # TODO remove
        return self.get_channel_info(self.bot.get_primary_conn().id).org_id

    def get_org_name(self):
        # TODO remove
        return self.get_channel_info(self.bot.get_primary_conn().id).org_name

    def get_channel_info(self, conn_id):
        return self.conns.get(conn_id, None)

    def get_channel_infos(self):
        return self.conns
