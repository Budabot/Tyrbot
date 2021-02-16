from core.conn import Conn
from core.decorators import instance
from core.aochat import server_packets
from core.dict_object import DictObject
from core.logger import Logger


@instance()
class PublicChannelService:
    ORG_CHANNEL_MESSAGE_EVENT = "org_channel_message"
    ORG_MSG_EVENT = "org_msg"

    ORG_MSG_CHANNEL_ID = 42949672961

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
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

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS org_name_cache (org_id INT NOT NULL, name VARCHAR(255) NOT NULL)")

    def handle_login_ok(self, conn: Conn, packet: server_packets.LoginOK):
        if not conn.is_main:
            return

    def add(self, conn: Conn, packet: server_packets.PublicChannelJoined):
        if not conn.is_main:
            return

        conn.channels[packet.channel_id] = packet
        if not conn.org_id and self.is_org_channel_id(packet.channel_id):
            conn.org_channel_id = packet.channel_id
            conn.org_id = 0x00ffffffff & packet.channel_id

            row = self.db.query_single("SELECT name FROM org_name_cache WHERE org_id = ?", [conn.org_id])

            if packet.name != "Clan (name unknown)":
                source = "chat_server"
                if not row:
                    self.db.exec("INSERT INTO org_name_cache (org_id, name) VALUES (?, ?)", [conn.org_id, packet.name])
                elif packet.name != row.name:
                    self.db.exec("UPDATE org_name_cache SET name = ? WHERE org_id = ?", [packet.name, conn.org_id])
                conn.org_name = packet.name
            elif row:
                source = "cache"
                conn.org_name = row.name
            else:
                source = "none"

            self.logger.info(f"Org info for '{conn.id}': {conn.org_name} ({conn.org_id}); source: '{source}'")

    def remove(self, conn: Conn, packet: server_packets.PublicChannelLeft):
        if not conn.is_main:
            return

        del conn.channels[packet.channel_id]

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
            self.event_service.fire_event(self.ORG_CHANNEL_MESSAGE_EVENT, DictObject({"char_id": packet.char_id,
                                                                                      "name": char_name,
                                                                                      "message": packet.message,
                                                                                      "extended_message": packet.extended_message,
                                                                                      "conn": conn}))
        elif packet.channel_id == self.ORG_MSG_CHANNEL_ID:
            char_name = self.character_service.get_char_name(packet.char_id)
            if packet.extended_message:
                message = packet.extended_message.get_message()
            else:
                message = packet.message
            self.logger.log_chat(conn.id, "Org Msg", char_name, message)
            self.event_service.fire_event(self.ORG_MSG_EVENT, DictObject({"char_id": packet.char_id,
                                                                          "name": char_name,
                                                                          "message": packet.message,
                                                                          "extended_message": packet.extended_message,
                                                                          "conn": conn}))

    def is_org_channel_id(self, channel_id):
        return channel_id >> 32 == 3
