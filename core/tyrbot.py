import inspect
import signal
import threading
import time
import requests
import re

from core.conn import Conn
from core.feature_flags import FeatureFlags
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
    PRIVATE_MSG_EVENT = "private_msg"
    LOGIN_FAILURE = "login_failure"

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
        self.version = "unknown"
        self.incoming_queue = FifoQueue()
        self.mass_message_queue = None
        self.conns = DictObject()
        self.primary_conn_id = None

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
        self.event_service.register_event_type(self.PRIVATE_MSG_EVENT)
        self.event_service.register_event_type(self.LOGIN_FAILURE)

    def start(self):
        self.setting_service.register("core.system", "symbol", "!", TextSettingType(["!", "#", "*", "@", "$", "+", "-"]), "Symbol for executing bot commands")

        self.setting_service.register("core.system", "org_channel_max_page_length", 4000,
                                      NumberSettingType([3000, 3500, 4000, 4500, 5500, 6500, 7500]),
                                      "Maximum size of blobs in org channel")
        self.setting_service.register("core.system", "private_message_max_page_length", 5500,
                                      NumberSettingType([3000, 3500, 4000, 4500, 5500, 6500, 7500]),
                                      "Maximum size of blobs in private messages")
        self.setting_service.register("core.system", "private_channel_max_page_length", 5500,
                                      NumberSettingType([3000, 3500, 4000, 4500, 5500, 6500, 7500]),
                                      "Maximum size of blobs in private channel")

        self.setting_service.register("core.system", "accept_commands_from_slave_bots", False, BooleanSettingType(),
                                      "Accept and respond to commands sent to slave bots (only applies if you have added slave bots in the config)")

        self.setting_service.register("core.colors", "header_color", "#FFFF00", ColorSettingType(), "Color for headers")
        self.setting_service.register("core.colors", "header2_color", "#FCA712", ColorSettingType(), "Color for sub-headers")
        self.setting_service.register("core.colors", "highlight_color", "#00BFFF", ColorSettingType(), "Color for highlight")
        self.setting_service.register("core.colors", "notice_color", "#FF8C00", ColorSettingType(), "Color for important notices")

        self.setting_service.register("core.colors", "neutral_color", "#E6E1A6", ColorSettingType(), "Color for neutral faction")
        self.setting_service.register("core.colors", "omni_color", "#FA8484", ColorSettingType(), "Color for omni faction")
        self.setting_service.register("core.colors", "clan_color", "#F79410", ColorSettingType(), "Color for clan faction")
        self.setting_service.register("core.colors", "unknown_color", "#FF0000", ColorSettingType(), "Color for unknown faction")

        self.setting_service.register("core.colors", "org_channel_color", "#89D2E8", ColorSettingType(), "Default org channel color")
        self.setting_service.register("core.colors", "private_channel_color", "#89D2E8", ColorSettingType(), "Default private channel color")
        self.setting_service.register("core.colors", "private_message_color", "#89D2E8", ColorSettingType(), "Default private message color")
        self.setting_service.register("core.colors", "blob_color", "#FFFFFF", ColorSettingType(), "Default blob content color")

        self.register_packet_handler(server_packets.PrivateMessage.id, self.handle_private_message, priority=40)

    def check_superadmin(self, char_id):
        char_name = self.character_service.resolve_char_to_name(char_id)
        return char_name == self.superadmin

    def connect(self, config):
        for i, bot_config in enumerate(config.bots):
            if "id" in bot_config:
                _id = bot_config.id
            else:
                _id = "bot" + str(i)

            if _id in self.conns:
                raise Exception(f"A connection with id {_id} already exists")

            if i == 0:
                self.primary_conn_id = _id
                wait_for_logged_in = 20
            else:
                wait_for_logged_in = 0

            conn = self.create_conn(_id)
            conn.connect(config.server.host, config.server.port)

            # only create the mass_message_queue if there is at least 1 non-main bot
            if not bot_config.is_main and not self.mass_message_queue:
                self.mass_message_queue = FifoQueue()

            login_success, packet = conn.login(bot_config.username, bot_config.password, bot_config.character, is_main=bot_config.is_main, wait_for_logged_in=wait_for_logged_in)
            if not login_success:
                self.event_service.fire_event(self.LOGIN_FAILURE, packet)

                if FeatureFlags.AUTO_UNFREEZE_ACCOUNTS and packet.id == server_packets.LoginError.id and packet.message and packet.message.endswith("/Account system denies login"):
                    self.unfreeze_account(bot_config)

                if i == 0 or not FeatureFlags.IGNORE_FAILED_BOTS_ON_LOGIN:
                    self.status = BotStatus.ERROR
                    return False
                else:
                    self.logger.warning("Skipping conn login")
            else:
                self.incoming_queue.put((conn, packet))

                self.conns[_id] = conn

                self.create_conn_thread(conn, None if bot_config.is_main or not bot_config.get("is_mass_message", True) else self.mass_message_queue)

        return True

    def unfreeze_account(self, bot_config):
        username = bot_config.username
        web_username = bot_config.web_username if "web_username" in bot_config else bot_config.username
        web_password = bot_config.web_password if "web_password" in bot_config else bot_config.password

        self.logger.info(f"({username}) - unfreezing account")
        minutes_delay = 10
        timeout = 5

        s = requests.Session()
        s.headers.update({"User-Agent": f"Tyrbot {self.version}"})
        
        # login
        login_response = s.post("https://account.anarchy-online.com/", data={"nickname": web_username, "password": web_password}, timeout=timeout)
        if login_response.status_code != 200 or login_response.url != "https://account.anarchy-online.com/account/":
            self.logger.warning(f"({username}) - login failed trying to unfreeze account, waiting {minutes_delay} to avoid lockout")
            time.sleep(minutes_delay * 60)
            return False

        time.sleep(5)

        # sub account handling
        if username != web_username or True:
            self.logger.info(f"({username}) - sub account detected")
            pattern = r"<a href=\"\/subscription\/(\d+)\">([a-z0-9]+)<\/a>"
            matches = re.findall(pattern, login_response.text)
            subscription_id = None
            for match in matches:
                if match[1] == username:
                    subscription_id = match[0]
                    self.logger.info(f"({username}) - found subscription id {subscription_id} for sub account")

            if subscription_id is None:
                self.logger.warning(f"({username}) - could not find subscription id for sub account to unfreeze account, waiting {minutes_delay} to avoid lockout")
                time.sleep(minutes_delay * 60)
                return False
            else:
                self.logger.info(f"({username}) - switching to sub account")
                sub_account_switch_response = s.get(f"https://account.anarchy-online.com/subscription/{subscription_id}", timeout=timeout)
                if sub_account_switch_response.status_code != 200 or sub_account_switch_response.url != "https://account.anarchy-online.com/account/":
                    self.logger.warning(f"({username}) - failed to switch to sub account, waiting {minutes_delay} to avoid lockout")
                    time.sleep(minutes_delay * 60)
                    return False
            
            time.sleep(5)

        # unfreeze
        reactivate_response = s.get("https://account.anarchy-online.com/uncancel_sub", timeout=timeout)
        if reactivate_response.status_code != 200 or reactivate_response.url != "https://account.anarchy-online.com/account/":
            self.logger.warning(f"({username}) - login failed trying to unfreeze account, waiting {minutes_delay} to avoid lockout")
            time.sleep(minutes_delay * 60)
            return False

        self.logger.info(f"({username}) - account unfrozen successfully")
        time.sleep(5)

        s.get("https://account.anarchy-online.com/log_out", timeout=timeout)

        return True

    def create_conn_thread(self, conn: Conn, mass_message_queue=None):
        def read_packets():
            try:
                while self.status == BotStatus.RUN:
                    packet = conn.read_packet(1)
                    if packet:
                        self.incoming_queue.put((conn, packet))

                    if mass_message_queue:
                        if FeatureFlags.FORCE_LARGE_MESSAGES_FROM_SLAVES:
                            if conn.packet_queue.is_empty():
                                packet = mass_message_queue.get_or_default(block=False)
                                if packet:
                                    conn.add_packets_to_queue([packet])
                        else:
                            while conn.packet_queue.is_empty():
                                packet = mass_message_queue.get_or_default(block=False)
                                if packet:
                                    conn.add_packets_to_queue([packet])
                                else:
                                    break

            except Exception as e:
                self.status = BotStatus.ERROR
                self.logger.error("", e)

        dthread = threading.Thread(target=read_packets, daemon=True)
        dthread.start()

    def create_conn(self, _id):
        def failure_callback():
            self.status = BotStatus.ERROR

        conn = Conn(_id, failure_callback)
        return conn

    def disconnect(self):
        # wait for all threads to stop reading packets, then disconnect them all
        time.sleep(2)
        for _id, conn in self.get_conns():
            conn.disconnect()

    def run(self):
        start = time.time()

        # wait for flood of packets from login to stop sending
        time_waited = 0
        while time_waited < 2:
            if not self.iterate(1):
                time_waited += 1

        self.logger.info("Login complete (%fs)" % (time.time() - start))

        start = time.time()
        self.event_service.fire_event("connect", None)
        self.event_service.run_timer_events_at_startup()
        self.event_service.check_for_timer_events(int(start))
        self.logger.info("Connect events finished (%fs)" % (time.time() - start))

        time_waited = 0
        while time_waited < 2:
            if not self.iterate(1):
                time_waited += 1

        self.ready = True
        timestamp = int(time.time())

        signal.signal(signal.SIGINT, self.handle_sigterm)
        signal.signal(signal.SIGTERM, self.handle_sigterm)

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
            raise Exception("Incorrect number of arguments for handler '%s.%s()'" % (handler.__module__, handler.__qualname__))

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
                self.logger.log_chat(conn, "SystemMessage", None, packet.extended_message.get_message())
            elif isinstance(packet, server_packets.PublicChannelMessage):
                packet = self.public_channel_message_ext_msg_handling(packet)
            elif isinstance(packet, server_packets.BuddyAdded) and packet.char_id == 0:
                return

            for handler in self.packet_handlers.get(packet.id, []):
                handler.handler(conn, packet)

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

    def send_org_message(self, msg, add_color=True, conn=None):
        if not conn:
            conn = self.get_primary_conn()

        if not conn.org_channel_id:
            self.logger.debug(f"Ignoring message to org channel for {conn.id} since the org_channel_id is unknown")
        else:
            color = self.setting_service.get("org_channel_color").get_font_color() if add_color else ""
            pages = self.get_text_pages(msg, conn, self.setting_service.get("org_channel_max_page_length").get_value())

            def map_page(page):
                return client_packets.PublicChannelMessage(conn.org_channel_id, color + page, "")

            conn.add_packets_to_queue(map(map_page, pages))

    def send_private_message(self, char_id, msg, add_color=True, conn=None):
        if not conn:
            conn = self.get_primary_conn()

        if char_id is None:
            raise Exception("Cannot send message, char_id is empty")
        else:
            color = self.setting_service.get("private_message_color").get_font_color() if add_color else ""
            pages = self.get_text_pages(msg, conn, self.setting_service.get("private_message_max_page_length").get_value())

            def map_page(page):
                self.logger.log_tell(conn, "To", self.character_service.get_char_name(char_id), page)
                return client_packets.PrivateMessage(char_id, color + page, "\0")

            conn.add_packets_to_queue(map(map_page, pages))

    def send_private_channel_message(self, msg, private_channel_id=None, add_color=True, conn=None):
        if not conn:
            conn = self.get_primary_conn()

        if private_channel_id is None:
            private_channel_id = conn.get_char_id()

        color = self.setting_service.get("private_channel_color").get_font_color() if add_color else ""
        pages = self.get_text_pages(msg, conn, self.setting_service.get("private_channel_max_page_length").get_value())
        for page in pages:
            packet = client_packets.PrivateChannelMessage(private_channel_id, color + page, "\0")
            conn.send_packet(packet)

    def send_mass_message(self, char_id, msg, add_color=True, conn=None):
        if not conn:
            conn = self.get_primary_conn()

        if not char_id:
            self.logger.warning("Could not send message to empty char_id")
        else:
            color = self.setting_service.get("private_message_color").get_font_color() if add_color else ""
            pages = self.get_text_pages(msg, conn, self.setting_service.get("private_message_max_page_length").get_value())
            for page in pages:
                packet = client_packets.PrivateMessage(char_id, color + page, "\0")
                if self.mass_message_queue:
                    self.mass_message_queue.put(packet)
                else:
                    conn.add_packets_to_queue([packet])

    def send_message_to_other_org_channels(self, msg, from_conn: Conn):
        for _id, conn in self.get_conns(lambda x: x.is_main and x.org_id and x != from_conn):
            self.send_org_message(msg, conn=conn)

    def handle_private_message(self, conn: Conn, packet: server_packets.PrivateMessage):
        char_name = self.character_service.get_char_name(packet.char_id)
        self.logger.log_tell(conn, "From", char_name, packet.message)
        self.event_service.fire_event(self.PRIVATE_MSG_EVENT, DictObject({"char_id": packet.char_id,
                                                                          "name": char_name,
                                                                          "message": packet.message,
                                                                          "conn": conn}))

    def get_text_pages(self, msg, conn, max_page_length):
        if isinstance(msg, ChatBlob):
            return self.text.paginate(msg, conn, max_page_length=max_page_length)
        else:
            return [self.text.format_message(msg, conn)]

    def is_ready(self):
        return self.ready

    def shutdown(self):
        self.status = BotStatus.SHUTDOWN

    def restart(self):
        self.status = BotStatus.RESTART

    def get_primary_conn_id(self):
        return self.primary_conn_id

    def get_primary_conn(self):
        return self.conns[self.get_primary_conn_id()]

    def get_conn_by_char_id(self, char_id):
        for _id, conn in self.get_conns():
            if char_id == conn.get_char_id():
                return conn
        return None

    def get_conn_by_org_id(self, org_id):
        for _id, conn in self.get_conns():
            if conn.org_id == org_id:
                return conn
        return None

    # placeholder to keep track of things that need to be fixed/updated
    def get_temp_conn(self):
        return self.get_primary_conn()

    def get_conns(self, conn_filter=None):
        if conn_filter:
            return [(_id, conn) for _id, conn in self.conns.items() if conn_filter(conn)]
        else:
            return self.conns.items()

    def handle_sigterm(self, signal_number, stackframe):
        self.logger.info(f"Shutting down due to signal '{signal_number}'")
        self.shutdown()
