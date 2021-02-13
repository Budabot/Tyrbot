import inspect
import threading
import time

from core.conn import Conn
from core.fifo_queue import FifoQueue
from core.dict_object import DictObject
from core.logger import Logger
from core.lookup.character_service import CharacterService
from core.public_channel_service import PublicChannelService
from core.setting_service import SettingService
from core.access_service import AccessService
from core.text import Text
from core.decorators import instance
from core.chat_blob import ChatBlob
from core.setting_types import TextSettingType, ColorSettingType, NumberSettingType, BooleanSettingType
from core.aochat import server_packets, client_packets
from core.aochat.extended_message import ExtendedMessage
from core.bot_status import BotStatus


@instance("bot")
class Tyrbot:
    CONNECT_EVENT = "connect"
    PACKET_EVENT = "packet"
    PRIVATE_MSG_EVENT = "private_msg"

    OUTGOING_ORG_MESSAGE_EVENT = "outgoing_org_message"
    OUTGOING_PRIVATE_MESSAGE_EVENT = "outgoing_private_message"
    OUTGOING_PRIVATE_CHANNEL_MESSAGE_EVENT = "outgoing_private_channel_message"

    def __init__(self):
        super().__init__()
        self.logger = Logger(__name__)
        self.ready = False
        self.packet_handlers = {}
        self.superadmin = None
        self.status: BotStatus = BotStatus.SHUTDOWN
        self.dimension = None
        self.last_timer_event = 0
        self.start_time = int(time.time())
        self.version = "0.5-beta"
        self.incoming_queue = FifoQueue()
        self.mass_message_queue = None
        self.conns = DictObject()

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.public_channel_service: PublicChannelService = registry.get_instance("public_channel_service")
        self.text: Text = registry.get_instance("text")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.access_service: AccessService = registry.get_instance("access_service")
        self.event_service = registry.get_instance("event_service")
        self.job_scheduler = registry.get_instance("job_scheduler")

    def init(self, config, registry, mmdb_parser):
        self.mmdb_parser = mmdb_parser
        self.superadmin = config.superadmin.capitalize()
        self.dimension = config.server.dimension

        self.db.exec("CREATE TABLE IF NOT EXISTS command_config (command VARCHAR(50) NOT NULL, sub_command VARCHAR(50) NOT NULL, access_level VARCHAR(50) NOT NULL, channel VARCHAR(50) NOT NULL, "
                     "module VARCHAR(50) NOT NULL, enabled SMALLINT NOT NULL, verified SMALLINT NOT NULL)")
        self.db.exec("CREATE TABLE IF NOT EXISTS event_config (event_type VARCHAR(50) NOT NULL, event_sub_type VARCHAR(50) NOT NULL, handler VARCHAR(255) NOT NULL, description VARCHAR(255) NOT NULL, "
                     "module VARCHAR(50) NOT NULL, enabled SMALLINT NOT NULL, verified SMALLINT NOT NULL, is_hidden SMALLINT NOT NULL)")
        self.db.exec("CREATE TABLE IF NOT EXISTS timer_event (event_type VARCHAR(50) NOT NULL, event_sub_type VARCHAR(50) NOT NULL, handler VARCHAR(255) NOT NULL, next_run INT NOT NULL)")
        self.db.exec("CREATE TABLE IF NOT EXISTS setting (name VARCHAR(50) NOT NULL, value VARCHAR(255) NOT NULL, description VARCHAR(255) NOT NULL, module VARCHAR(50) NOT NULL, verified SMALLINT NOT NULL)")
        self.db.exec("CREATE TABLE IF NOT EXISTS command_alias (alias VARCHAR(50) NOT NULL, command VARCHAR(1024) NOT NULL, enabled SMALLINT NOT NULL)")
        self.db.exec("CREATE TABLE IF NOT EXISTS command_usage (command VARCHAR(255) NOT NULL, handler VARCHAR(255) NOT NULL, char_id INT NOT NULL, channel VARCHAR(20) NOT NULL, created_at INT NOT NULL)")
        self.db.exec("CREATE TABLE IF NOT EXISTS ban_list (char_id INT NOT NULL, sender_char_id INT NOT NULL, created_at INT NOT NULL, finished_at INT NOT NULL, reason VARCHAR(255) NOT NULL, ended_early SMALLINT NOT NULL)")

        self.db.exec("UPDATE db_version SET verified = 0")
        self.db.exec("UPDATE db_version SET verified = 1 WHERE file = 'db_version'")

        # prepare commands, events, and settings
        self.db.exec("UPDATE command_config SET verified = 0")
        self.db.exec("UPDATE event_config SET verified = 0")
        self.db.exec("UPDATE setting SET verified = 0")

        with self.db.transaction():
            registry.pre_start_all()
            registry.start_all()

        # remove commands, events, and settings that are no longer registered
        self.db.exec("DELETE FROM db_version WHERE verified = 0")
        self.db.exec("DELETE FROM command_config WHERE verified = 0")
        self.db.exec("DELETE FROM event_config WHERE verified = 0")
        self.db.exec("DELETE FROM timer_event WHERE handler NOT IN (SELECT handler FROM event_config WHERE event_type = ?)", ["timer"])
        self.db.exec("DELETE FROM setting WHERE verified = 0")

        self.status = BotStatus.RUN

    def pre_start(self):
        self.access_service.register_access_level("superadmin", 10, self.check_superadmin)
        self.event_service.register_event_type(self.CONNECT_EVENT)
        self.event_service.register_event_type(self.PACKET_EVENT)
        self.event_service.register_event_type(self.PRIVATE_MSG_EVENT)
        self.event_service.register_event_type(self.OUTGOING_ORG_MESSAGE_EVENT)
        self.event_service.register_event_type(self.OUTGOING_PRIVATE_MESSAGE_EVENT)
        self.event_service.register_event_type(self.OUTGOING_PRIVATE_CHANNEL_MESSAGE_EVENT)

    def start(self):
        self.setting_service.register_new("core.system", "symbol", "!", TextSettingType(["!", "#", "*", "@", "$", "+", "-"]), "Symbol for executing bot commands")

        self.setting_service.register_new("core.system", "org_channel_max_page_length", 7500,
                                          NumberSettingType([4500, 6000, 7500, 9000, 10500, 12000]),
                                          "Maximum size of blobs in org channel")
        self.setting_service.register_new("core.system", "private_message_max_page_length", 7500,
                                          NumberSettingType([4500, 6000, 7500, 9000, 10500, 12000]),
                                          "Maximum size of blobs in private messages")
        self.setting_service.register_new("core.system", "private_channel_max_page_length", 7500,
                                          NumberSettingType([4500, 6000, 7500, 9000, 10500, 12000]),
                                          "Maximum size of blobs in private channel")

        self.setting_service.register_new("core.system", "org_id", "", NumberSettingType(allow_empty=True), "Override the default org id",
                                          "This setting is is for development/debug purposes and should not be changed unless you understand the implications")
        self.setting_service.register_new("core.system", "org_name", "", TextSettingType(allow_empty=True), "The exact org name of the bot",
                                          "This setting is automatically set by the bot and should not be changed manually")

        self.setting_service.register_new("core.system", "accept_commands_from_slave_bots", False, BooleanSettingType(),
                                          "Accept and respond to commands sent to slave bots (only applies if you have added slave bots in the config)")

        self.setting_service.register_new("core.colors", "header_color", "#FFFF00", ColorSettingType(), "Color for headers")
        self.setting_service.register_new("core.colors", "header2_color", "#FCA712", ColorSettingType(), "Color for sub-headers")
        self.setting_service.register_new("core.colors", "highlight_color", "#00BFFF", ColorSettingType(), "Color for highlight")
        self.setting_service.register_new("core.colors", "notice_color", "#FF8C00", ColorSettingType(), "Color for important notices")

        self.setting_service.register_new("core.colors", "neutral_color", "#E6E1A6", ColorSettingType(), "Color for neutral faction")
        self.setting_service.register_new("core.colors", "omni_color", "#FA8484", ColorSettingType(), "Color for omni faction")
        self.setting_service.register_new("core.colors", "clan_color", "#F79410", ColorSettingType(), "Color for clan faction")
        self.setting_service.register_new("core.colors", "unknown_color", "#FF0000", ColorSettingType(), "Color for unknown faction")

        self.setting_service.register_new("core.colors", "org_channel_color", "#89D2E8", ColorSettingType(), "Default org channel color")
        self.setting_service.register_new("core.colors", "private_channel_color", "#89D2E8", ColorSettingType(), "Default private channel color")
        self.setting_service.register_new("core.colors", "private_message_color", "#89D2E8", ColorSettingType(), "Default private message color")
        self.setting_service.register_new("core.colors", "blob_color", "#FFFFFF", ColorSettingType(), "Default blob content color")

        self.register_packet_handler(server_packets.PrivateMessage.id, self.handle_private_message, priority=40)

    def check_superadmin(self, char_id):
        char_name = self.character_service.resolve_char_to_name(char_id)
        return char_name == self.superadmin

    def connect(self, config):
        conn = self.create_conn("main")
        conn.connect(config.server.host, config.server.port)
        packet = conn.login(config.username, config.password, config.character, is_main=True)
        if not packet:
            self.status = BotStatus.ERROR
            return False
        else:
            self.incoming_queue.put((conn, packet))

        self.create_conn_thread(conn, None)

        if "slaves" in config:
            self.mass_message_queue = FifoQueue()
            for i, slave in enumerate(config.slaves):
                conn = self.create_conn("slave" + str(i))
                conn.connect(config.server.host, config.server.port)

                packet = conn.login(slave.username, slave.password, slave.character, is_main=False)
                if not packet:
                    self.status = BotStatus.ERROR
                    return False
                else:
                    self.incoming_queue.put((conn, packet))

                self.create_conn_thread(conn, self.mass_message_queue)

        return True

    def create_conn_thread(self, conn: Conn, mass_message_queue=None):
        def read_packets():
            try:
                while self.status == BotStatus.RUN:
                    packet = conn.read_packet(1)
                    if packet:
                        self.incoming_queue.put((conn, packet))

                    while mass_message_queue and not mass_message_queue.empty() and conn.packet_queue.is_empty():
                        packet = mass_message_queue.get_or_default(block=False)
                        if packet:
                            conn.add_packet_to_queue(packet)

            except (EOFError, OSError) as e:
                self.status = BotStatus.ERROR
                self.logger.error("", e)
                raise e

        dthread = threading.Thread(target=read_packets, daemon=True)
        dthread.start()

    def create_conn(self, _id):
        if _id in self.conns:
            raise Exception(f"A connection with id {_id} already exists")

        def failure_callback():
            self.status = BotStatus.ERROR

        conn = Conn(_id, failure_callback)
        self.conns[_id] = conn
        return conn

    # passthrough
    def send_packet(self, packet):
        self.conns["main"].send_packet(packet)

    def disconnect(self):
        # wait for all threads to stop reading packets, then disconnect them all
        time.sleep(2)
        for _id, conn in self.conns.items():
            conn.disconnect()

    def run(self):
        start = time.time()

        # wait for flood of packets from login to stop sending
        time_waited = 0
        while time_waited < 5:
            if not self.iterate(1):
                time_waited += 1

        self.logger.info("Login complete (%fs)" % (time.time() - start))

        start = time.time()
        self.event_service.fire_event("connect", None)
        self.event_service.run_timer_events_at_startup()
        self.logger.info("Connect events finished (%fs)" % (time.time() - start))

        self.ready = True
        timestamp = int(time.time())

        while self.status == BotStatus.RUN:
            try:
                timestamp = int(time.time())
                self.check_for_timer_events(timestamp)

                self.iterate()
            except Exception as e:
                self.logger.error("", e)

        # run any pending jobs/events
        self.check_for_timer_events(timestamp + 1)

        return self.status

    def check_for_timer_events(self, timestamp):
        # timer events will execute no more often than once per second
        if self.last_timer_event < timestamp:
            self.last_timer_event = timestamp
            self.job_scheduler.check_for_scheduled_jobs(timestamp)
            self.event_service.check_for_timer_events(timestamp)

    def register_packet_handler(self, packet_id: int, handler, priority=50):
        """
        Call during pre_start

        Args:
            packet_id: int
            handler: (conn, packet) -> void
            priority: int
        """

        if len(inspect.signature(handler).parameters) != 2:
            raise Exception("Incorrect number of arguments for handler '%s.%s()'" % (handler.__module__, handler.__name__))

        handlers = self.packet_handlers.get(packet_id, [])
        handlers.append(DictObject({"priority": priority, "handler": handler}))
        self.packet_handlers[packet_id] = sorted(handlers, key=lambda x: x.priority)

    def remove_packet_handler(self, packet_id, handler):
        handlers = self.packet_handlers.get(packet_id, [])
        for h in handlers:
            if h.handler == handler:
                handlers.remove(h)

    def iterate(self, timeout=0.1):
        conn, packet = self.incoming_queue.get_or_default(block=True, timeout=timeout, default=(None, None))
        if packet:
            if isinstance(packet, server_packets.SystemMessage):
                packet = self.system_message_ext_msg_handling(packet)
                self.logger.log_chat(conn.id, "SystemMessage", None, packet.extended_message.get_message())
            elif isinstance(packet, server_packets.PublicChannelMessage):
                packet = self.public_channel_message_ext_msg_handling(packet)
            if isinstance(packet, server_packets.BuddyAdded):
                if packet.char_id == 0:
                    return

            for handler in self.packet_handlers.get(packet.id, []):
                handler.handler(conn, packet)

            self.event_service.fire_event("packet:" + str(packet.id), packet)

        return packet

    def public_channel_message_ext_msg_handling(self, packet: server_packets.PublicChannelMessage):
        msg = packet.message
        if msg.startswith("~&") and msg.endswith("~"):
            try:
                msg = msg[2:-1].encode("utf-8")
                category_id = self.mmdb_parser.read_base_85(msg[0:5])
                instance_id = self.mmdb_parser.read_base_85(msg[5: 10])
                template = self.mmdb_parser.get_message_string(category_id, instance_id)
                params = self.mmdb_parser.parse_params(msg[10:])
                packet.extended_message = ExtendedMessage(category_id, instance_id, template, params)
            except Exception as e:
                self.logger.error("Error handling extended message for packet: " + str(packet), e)

        return packet

    def system_message_ext_msg_handling(self, packet: server_packets.SystemMessage):
        try:
            category_id = 20000
            instance_id = packet.message_id
            template = self.mmdb_parser.get_message_string(category_id, instance_id)
            params = self.mmdb_parser.parse_params(packet.message_args)
            packet.extended_message = ExtendedMessage(category_id, instance_id, template, params)
        except Exception as e:
            self.logger.error("Error handling extended message: " + str(packet), e)

        return packet

    def send_org_message(self, msg, add_color=True, fire_outgoing_event=True, conn=None):
        if not conn:
            conn = self.get_primary_conn()

        org_channel_id = self.public_channel_service.org_channel_id
        if org_channel_id is None:
            self.logger.debug("ignoring message to org channel since the org_channel_id is unknown")
        else:
            color = self.setting_service.get("org_channel_color").get_font_color() if add_color else ""
            pages = self.get_text_pages(msg, self.setting_service.get("org_channel_max_page_length").get_value())
            for page in pages:
                packet = client_packets.PublicChannelMessage(org_channel_id, color + page, "")
                conn.add_packet_to_queue(packet)

            if fire_outgoing_event:
                self.event_service.fire_event(self.OUTGOING_ORG_MESSAGE_EVENT, DictObject({"org_channel_id": org_channel_id,
                                                                                           "message": msg}))

    def send_private_message(self, char_id, msg, add_color=True, fire_outgoing_event=True, conn=None):
        if not conn:
            conn = self.get_primary_conn()

        if char_id is None:
            raise Exception("Cannot send message, char_id is empty")
        else:
            color = self.setting_service.get("private_message_color").get_font_color() if add_color else ""
            pages = self.get_text_pages(msg, self.setting_service.get("private_message_max_page_length").get_value())
            for page in pages:
                self.logger.log_tell(conn.id, "To", self.character_service.get_char_name(char_id), page)
                packet = client_packets.PrivateMessage(char_id, color + page, "\0")
                conn.add_packet_to_queue(packet)

            if fire_outgoing_event:
                self.event_service.fire_event(self.OUTGOING_PRIVATE_MESSAGE_EVENT, DictObject({"char_id": char_id,
                                                                                               "message": msg}))

    def send_private_channel_message(self, msg, private_channel_id=None, add_color=True, fire_outgoing_event=True, conn=None):
        if not conn:
            conn = self.get_primary_conn()

        if private_channel_id is None:
            private_channel_id = self.get_char_id()

        color = self.setting_service.get("private_channel_color").get_font_color() if add_color else ""
        pages = self.get_text_pages(msg, self.setting_service.get("private_channel_max_page_length").get_value())
        for page in pages:
            packet = client_packets.PrivateChannelMessage(private_channel_id, color + page, "\0")
            conn.send_packet(packet)

        if fire_outgoing_event and private_channel_id == self.get_char_id():
            self.event_service.fire_event(self.OUTGOING_PRIVATE_CHANNEL_MESSAGE_EVENT, DictObject({"private_channel_id": private_channel_id,
                                                                                                   "message": msg}))

    def send_mass_message(self, char_id, msg, add_color=True, log_message=False):
        if not char_id:
            self.logger.warning("Could not send message to empty char_id")
        else:
            color = self.setting_service.get("private_message_color").get_font_color() if add_color else ""
            pages = self.get_text_pages(msg, self.setting_service.get("private_message_max_page_length").get_value())
            for page in pages:
                if log_message:
                    self.logger.log_tell("spam", "To", self.character_service.get_char_name(char_id), page)

                if self.mass_message_queue:
                    packet = client_packets.PrivateMessage(char_id, color + page, "\0")
                    self.mass_message_queue.put(packet)
                else:
                    packet = client_packets.PrivateMessage(char_id, color + page, "spam")
                    self.conns["main"].send_packet(packet)

    def handle_private_message(self, conn: Conn, packet: server_packets.PrivateMessage):
        self.logger.log_tell(conn.id, "From", self.character_service.get_char_name(packet.char_id), packet.message)
        self.event_service.fire_event(self.PRIVATE_MSG_EVENT, packet)

    def get_text_pages(self, msg, max_page_length):
        if isinstance(msg, ChatBlob):
            return self.text.paginate(msg, max_page_length=max_page_length)
        else:
            return [self.text.format_message(msg)]

    def is_ready(self):
        return self.ready

    def shutdown(self):
        self.status = BotStatus.SHUTDOWN

    def restart(self):
        self.status = BotStatus.RESTART

    def get_char_name(self):
        return self.get_primary_conn().char_name

    def get_char_id(self):
        return self.get_primary_conn().char_id

    def get_primary_conn(self):
        return self.conns["main"]
