from core.conn import Conn
from core.dict_object import DictObject
from core.logger import Logger
from core.decorators import instance
from core.aochat import server_packets, client_packets


@instance()
class PrivateChannelService:
    PRIVATE_CHANNEL_MESSAGE_EVENT = "private_channel_message"
    PRIVATE_CHANNEL_COMMAND_EVENT = "private_channel_command"
    JOINED_PRIVATE_CHANNEL_EVENT = "private_channel_joined"
    LEFT_PRIVATE_CHANNEL_EVENT = "private_channel_left"

    PRIVATE_CHANNEL_COMMAND = "priv"

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.setting_service = registry.get_instance("setting_service")
        self.event_service = registry.get_instance("event_service")
        self.character_service = registry.get_instance("character_service")
        self.access_service = registry.get_instance("access_service")
        self.command_service = registry.get_instance("command_service")

    def pre_start(self):
        self.bot.register_packet_handler(server_packets.PrivateChannelClientJoined.id, self.handle_private_channel_client_joined)
        self.bot.register_packet_handler(server_packets.PrivateChannelClientLeft.id, self.handle_private_channel_client_left)
        self.bot.register_packet_handler(server_packets.PrivateChannelMessage.id, self.handle_private_channel_message)

        self.event_service.register_event_type(self.JOINED_PRIVATE_CHANNEL_EVENT)
        self.event_service.register_event_type(self.LEFT_PRIVATE_CHANNEL_EVENT)
        self.event_service.register_event_type(self.PRIVATE_CHANNEL_MESSAGE_EVENT)
        self.event_service.register_event_type(self.PRIVATE_CHANNEL_COMMAND_EVENT)

        self.access_service.register_access_level("guest", 90, self.in_any_private_channel)

        self.command_service.register_command_channel("Private Channel", self.PRIVATE_CHANNEL_COMMAND)

    def handle_private_channel_message(self, conn: Conn, packet: server_packets.PrivateChannelMessage):
        char_name = self.character_service.get_char_name(packet.char_id)
        if packet.private_channel_id != conn.char_id:
            # channel_name = self.character_service.get_char_name(packet.private_channel_id)
            # self.logger.log_chat(conn, f"Private Channel({channel_name})", char_name, packet.message)
            pass
        else:
            self.logger.log_chat(conn, "Private Channel", char_name, packet.message)

            if not conn.is_main or conn.char_id == packet.char_id:
                return

            if not self.handle_private_channel_command(conn, packet):
                self.event_service.fire_event(self.PRIVATE_CHANNEL_MESSAGE_EVENT, DictObject({"char_id": packet.char_id,
                                                                                              "name": char_name,
                                                                                              "message": packet.message,
                                                                                              "conn": conn}))

    def handle_private_channel_client_joined(self, conn: Conn, packet: server_packets.PrivateChannelClientJoined):
        char_name = self.character_service.get_char_name(packet.char_id)
        if packet.private_channel_id != conn.char_id:
            # channel_name = self.character_service.get_char_name(packet.private_channel_id)
            # self.logger.log_chat(conn, f"Private Channel({channel_name}", None, f"{char_name} joined the channel.")
            pass
        else:
            self.logger.log_chat(conn, "Private Channel", None, f"{char_name} joined the channel.")
            conn.private_channel[packet.char_id] = packet

            if conn.is_main:
                self.event_service.fire_event(self.JOINED_PRIVATE_CHANNEL_EVENT, DictObject({"char_id": packet.char_id,
                                                                                             "name": char_name,
                                                                                             "conn": conn}))

    def handle_private_channel_client_left(self, conn: Conn, packet: server_packets.PrivateChannelClientLeft):
        char_name = self.character_service.get_char_name(packet.char_id)
        if packet.private_channel_id != conn.char_id:
            # channel_name = self.character_service.get_char_name(packet.private_channel_id)
            # self.logger.log_chat(conn, f"Private Channel({channel_name})", None, f"{char_name} left the channel.")
            pass
        else:
            self.logger.log_chat(conn, "Private Channel", None, f"{char_name} left the channel.")
            del conn.private_channel[packet.char_id]

            if conn.is_main:
                self.event_service.fire_event(self.LEFT_PRIVATE_CHANNEL_EVENT, DictObject({"char_id": packet.char_id,
                                                                                           "name": char_name,
                                                                                           "conn": conn}))

    def handle_private_channel_command(self, conn: Conn, packet: server_packets.PrivateChannelMessage):
        if not self.setting_service.get("accept_commands_from_slave_bots").get_value() and not conn.is_main:
            return False

        # since the command symbol is required in the private channel,
        # the command_str must have length of at least 2 in order to be valid,
        # otherwise it is ignored
        if len(packet.message) < 2:
            return False

        self.event_service.fire_event(self.PRIVATE_CHANNEL_COMMAND_EVENT,
                                      DictObject({"org_channel_id": packet.private_channel_id, "message": packet.message, "conn": conn}))

        # ignore leading space
        message = packet.message.lstrip()

        def reply(msg):
            self.bot.send_private_channel_message(msg, private_channel_id=conn.char_id, conn=conn)
            self.event_service.fire_event(self.PRIVATE_CHANNEL_COMMAND_EVENT,
                                          DictObject({"org_channel_id": packet.private_channel_id, "message": msg, "conn": conn}))

        if message.startswith(self.setting_service.get("symbol").get_value()) and packet.private_channel_id == conn.get_char_id():
            self.command_service.process_command(
                self.command_service.trim_command_symbol(message),
                self.PRIVATE_CHANNEL_COMMAND,
                packet.char_id,
                reply,
                conn)

        return True

    def invite(self, char_id, conn: Conn):
        if char_id != conn.char_id and conn.is_main:
            conn.send_packet(client_packets.PrivateChannelInvite(char_id))

    def kick(self, char_id, conn: Conn):
        if char_id != conn.char_id:
            conn.send_packet(client_packets.PrivateChannelKick(char_id))

    def kick_from_all(self, char_id):
        for _id, conn in self.bot.get_conns():
            if char_id in conn.private_channel:
                conn.send_packet(client_packets.PrivateChannelKick(char_id))

    def kickall(self, conn: Conn):
        conn.send_packet(client_packets.PrivateChannelKickAll())

    def in_any_private_channel(self, char_id):
        for _id, conn in self.bot.get_conns():
            if char_id in conn.private_channel:
                return True
        return False
