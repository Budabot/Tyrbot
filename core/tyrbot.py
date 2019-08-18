from core.aochat.bot import Bot
from core.dict_object import DictObject
from core.lookup.character_service import CharacterService
from core.public_channel_service import PublicChannelService
from core.setting_service import SettingService
from core.access_service import AccessService
from core.text import Text
from core.decorators import instance
from core.chat_blob import ChatBlob
from core.setting_types import TextSettingType, ColorSettingType, NumberSettingType
from core.aochat import server_packets, client_packets
from core.aochat.extended_message import ExtendedMessage
from core.aochat.delay_queue import DelayQueue
from core.bot_status import BotStatus
from __init__ import flatmap
import os
import time


@instance("bot")
class Tyrbot(Bot):
    CONNECT_EVENT = "connect"
    PACKET_EVENT = "packet"
    PRIVATE_MSG_EVENT = "private_msg"

    OUTGOING_ORG_MESSAGE_EVENT = "outgoing_org_message"
    OUTGOING_PRIVATE_MESSAGE_EVENT = "outgoing_private_message"
    OUTGOING_PRIVATE_CHANNEL_MESSAGE_EVENT = "outgoing_private_channel_message"

    def __init__(self):
        super().__init__()
        self.ready = False
        self.packet_handlers = {}
        self.superadmin = None
        self.status: BotStatus = BotStatus.SHUTDOWN
        self.dimension = None
        self.packet_queue = DelayQueue(2, 2.5)
        self.last_timer_event = 0
        self.start_time = int(time.time())
        self.version = "0.4-beta"

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.public_channel_service: PublicChannelService = registry.get_instance("public_channel_service")
        self.text: Text = registry.get_instance("text")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.access_service: AccessService = registry.get_instance("access_service")
        self.event_service = registry.get_instance("event_service")
        self.job_scheduler = registry.get_instance("job_scheduler")

    def init(self, config, registry, paths, mmdb_parser):
        self.mmdb_parser = mmdb_parser
        self.superadmin = config.superadmin.capitalize()
        self.dimension = config.server.dimension

        self.db.exec("UPDATE db_version SET verified = 0")
        self.db.exec("UPDATE db_version SET verified = 1 WHERE file = 'db_version'")

        self.load_sql_files(paths)

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

        self.db.exec("UPDATE event_config SET enabled = 1 WHERE is_hidden = 1")

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
        self.setting_service.register("symbol", "!", "Symbol for executing bot commands", TextSettingType(["!", "#", "*", "@", "$", "+", "-"]), "core.system")

        self.setting_service.register("org_channel_max_page_length", 7500, "Maximum size of blobs in org channel",
                                      NumberSettingType([4500, 6000, 7500, 9000, 10500, 12000]), "core.system")
        self.setting_service.register("private_message_max_page_length", 7500, "Maximum size of blobs in private messages",
                                      NumberSettingType([4500, 6000, 7500, 9000, 10500, 12000]), "core.system",)
        self.setting_service.register("private_channel_max_page_length", 7500, "Maximum size of blobs in private channel",
                                      NumberSettingType([4500, 6000, 7500, 9000, 10500, 12000]), "core.system")

        self.setting_service.register("header_color", "#FFFF00", "color for headers", ColorSettingType(), "core.colors")
        self.setting_service.register("header2_color", "#FCA712", "color for sub-headers", ColorSettingType(), "core.colors")
        self.setting_service.register("highlight_color", "#00BFFF", "color for highlight", ColorSettingType(), "core.colors")
        self.setting_service.register("notice_color", "#FF8C00", "color for important notices", ColorSettingType(), "core.colors")

        self.setting_service.register("neutral_color", "#E6E1A6", "color for neutral faction", ColorSettingType(), "core.colors")
        self.setting_service.register("omni_color", "#FA8484", "color for omni faction", ColorSettingType(), "core.colors")
        self.setting_service.register("clan_color", "#F79410", "color for clan faction", ColorSettingType(), "core.colors")
        self.setting_service.register("unknown_color", "#FF0000", "color for unknown faction", ColorSettingType(), "core.colors")

        self.setting_service.register("org_channel_color", "#89D2E8", "default org channel color", ColorSettingType(), "core.colors")
        self.setting_service.register("private_channel_color", "#89D2E8", "default private channel color", ColorSettingType(), "core.colors")
        self.setting_service.register("private_message_color", "#89D2E8", "default private message color", ColorSettingType(), "core.colors")
        self.setting_service.register("blob_color", "#FFFFFF", "default blob content color", ColorSettingType(), "core.colors")

        self.add_packet_handler(server_packets.PrivateMessage.id, self.handle_private_message, priority=40)

    def check_superadmin(self, char_id):
        char_name = self.character_service.resolve_char_to_name(char_id)
        return char_name == self.superadmin

    def run(self):
        start = time.time()

        # wait for flood of packets from login to stop sending
        time_waited = 0
        while time_waited < 5:
            if not self.iterate():
                time_waited += 1

        self.logger.info("Login complete (%fs)" % (time.time() - start))

        start = time.time()
        self.event_service.fire_event("connect", None)
        self.logger.info("Connect events finished (%fs)" % (time.time() - start))

        self.ready = True

        # TODO this prevents restarting as a way to clear the packet queue
        while self.status == BotStatus.RUN or len(self.packet_queue) > 0:
            try:
                timestamp = int(time.time())

                # timer events will execute no more often than once per second
                if self.last_timer_event < timestamp:
                    self.last_timer_event = timestamp
                    self.job_scheduler.check_for_scheduled_jobs(timestamp)
                    self.event_service.check_for_timer_events(timestamp)

                self.iterate()
            except (EOFError, OSError) as e:
                raise e
            except Exception as e:
                self.logger.error("", e)

        return self.status

    def add_packet_handler(self, packet_id: int, handler, priority=50):
        handlers = self.packet_handlers.get(packet_id, [])
        handlers.append(DictObject({"priority": priority, "handler": handler}))
        self.packet_handlers[packet_id] = sorted(handlers, key=lambda x: x.priority)

    def remove_packet_handler(self, packet_id, handler):
        handlers = self.packet_handlers.get(packet_id, [])
        for h in handlers:
            if h.handler == handler:
                handlers.remove(h)

    def iterate(self):
        packet = self.read_packet(1)
        if packet:
            if isinstance(packet, server_packets.SystemMessage):
                packet = self.system_message_ext_msg_handling(packet)
            elif isinstance(packet, server_packets.PublicChannelMessage):
                packet = self.public_channel_message_ext_msg_handling(packet)

            for handler in self.packet_handlers.get(packet.id, []):
                handler.handler(packet)

            self.event_service.fire_event("packet:" + str(packet.id), packet)

        self.check_outgoing_message_queue()

        return packet

    def check_outgoing_message_queue(self):
        # check packet queue for outgoing packets
        outgoing_packet = self.packet_queue.dequeue()
        while outgoing_packet:
            self.send_packet(outgoing_packet)
            outgoing_packet = self.packet_queue.dequeue()

        num_messages = len(self.packet_queue)
        if num_messages > 30:
            self.logger.warning("automatically clearing outgoing message queue (%d messages)" % num_messages)
            self.packet_queue.clear()
        elif num_messages > 10:
            self.logger.warning("%d messages in outgoing message queue" % num_messages)

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
            self.logger.log_chat("SystemMessage", None, packet.extended_message.get_message())
        except Exception as e:
            self.logger.error("Error handling extended message: " + str(packet), e)

        return packet

    def send_org_message(self, msg, add_color=True, fire_outgoing_event=True):
        org_channel_id = self.public_channel_service.org_channel_id
        if org_channel_id is None:
            self.logger.debug("ignoring message to org channel since the org_channel_id is unknown")
        else:
            color = self.setting_service.get("org_channel_color").get_font_color() if add_color else ""
            pages = self.get_text_pages(msg, self.setting_service.get("org_channel_max_page_length").get_value())
            for page in pages:
                packet = client_packets.PublicChannelMessage(org_channel_id, color + page, "")
                self.packet_queue.enqueue(packet)
                self.check_outgoing_message_queue()

            if fire_outgoing_event:
                self.event_service.fire_event(self.OUTGOING_ORG_MESSAGE_EVENT, DictObject({"org_channel_id": org_channel_id,
                                                                                           "message": msg}))

    def send_private_message(self, char, msg, add_color=True, fire_outgoing_event=True):
        char_id = self.character_service.resolve_char_to_id(char)
        if char_id is None:
            self.logger.warning("Could not send message to %s, could not find char id" % char)
        else:
            color = self.setting_service.get("private_message_color").get_font_color() if add_color else ""
            pages = self.get_text_pages(msg, self.setting_service.get("private_message_max_page_length").get_value())
            for page in pages:
                self.logger.log_tell("To", self.character_service.get_char_name(char_id), page)
                packet = client_packets.PrivateMessage(char_id, color + page, "\0")
                self.packet_queue.enqueue(packet)
                self.check_outgoing_message_queue()

            if fire_outgoing_event:
                self.event_service.fire_event(self.OUTGOING_PRIVATE_MESSAGE_EVENT, DictObject({"char_id": char_id,
                                                                                               "message": msg}))

    def send_private_channel_message(self, msg, private_channel=None, add_color=True, fire_outgoing_event=True):
        if private_channel is None:
            private_channel = self.char_id

        private_channel_id = self.character_service.resolve_char_to_id(private_channel)
        if private_channel_id is None:
            self.logger.warning("Could not send message to private channel %s, could not find private channel" % private_channel)
        else:
            color = self.setting_service.get("private_channel_color").get_font_color() if add_color else ""
            pages = self.get_text_pages(msg, self.setting_service.get("private_channel_max_page_length").get_value())
            for page in pages:
                packet = client_packets.PrivateChannelMessage(private_channel_id, color + page, "\0")
                self.send_packet(packet)

            if fire_outgoing_event and private_channel_id == self.char_id:
                self.event_service.fire_event(self.OUTGOING_PRIVATE_CHANNEL_MESSAGE_EVENT, DictObject({"private_channel_id": private_channel_id,
                                                                                                       "message": msg}))

    def handle_private_message(self, packet: server_packets.PrivateMessage):
        self.logger.log_tell("From", self.character_service.get_char_name(packet.char_id), packet.message)
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

    def load_sql_files(self, paths):
        dirs = flatmap(lambda x: os.walk(x), paths)
        dirs = filter(lambda y: not y[0].endswith("__pycache__"), dirs)

        def get_files(tup):
            return map(lambda x: os.path.join(tup[0], x), tup[2])

        # get files from subdirectories
        files = flatmap(get_files, dirs)
        files = filter(lambda z: z.endswith(".sql"), files)

        base_path = os.getcwd()
        for file in files:
            self.db.load_sql_file(file, base_path)
