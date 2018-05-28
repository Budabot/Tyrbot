from core.aochat.bot import Bot
from core.buddy_manager import BuddyManager
from core.lookup.character_manager import CharacterManager
from core.public_channel_manager import PublicChannelManager
from core.setting_manager import SettingManager
from core.access_manager import AccessManager
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
    def __init__(self):
        super().__init__()
        self.ready = False
        self.packet_handlers = {}
        self.org_id = None
        self.org_name = None
        self.superadmin = None
        self.status: BotStatus = BotStatus.SHUTDOWN
        self.dimension = None
        self.packet_queue = DelayQueue(2, 2.5)
        self.last_timer_event = 0

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.buddy_manager: BuddyManager = registry.get_instance("buddy_manager")
        self.character_manager: CharacterManager = registry.get_instance("character_manager")
        self.public_channel_manager: PublicChannelManager = registry.get_instance("public_channel_manager")
        self.text: Text = registry.get_instance("text")
        self.setting_manager: SettingManager = registry.get_instance("setting_manager")
        self.access_manager: AccessManager = registry.get_instance("access_manager")
        self.command_manager = registry.get_instance("command_manager")
        self.event_manager = registry.get_instance("event_manager")
        self.job_scheduler = registry.get_instance("job_scheduler")

    def init(self, config, registry, paths, mmdb_parser):
        self.mmdb_parser = mmdb_parser
        self.superadmin = config.superadmin.capitalize()
        self.dimension = 5

        if config.database.type == "sqlite":
            self.db.connect_sqlite(config.database.name)
        elif config.database.type == "mysql":
            self.db.connect_mysql(config.database.host, config.database.username, config.database.password, config.database.name)
        else:
            raise Exception("Unknown database type '%s'" % config.database.type)

        self.load_sql_files(paths)

        # prepare commands, events, and settings
        self.db.exec("UPDATE command_config SET verified = 0")
        self.db.exec("UPDATE event_config SET verified = 0")
        self.db.exec("UPDATE setting SET verified = 0")

        registry.pre_start_all()
        registry.start_all()

        # remove commands, events, and settings that are no longer registered
        self.db.exec("DELETE FROM command_config WHERE verified = 0")
        self.db.exec("DELETE FROM event_config WHERE verified = 0")
        self.db.exec("DELETE FROM timer_event WHERE handler NOT IN (SELECT handler FROM event_config WHERE event_type = ?)", ["timer"])
        self.db.exec("DELETE FROM setting WHERE verified = 0")

        self.status = BotStatus.RUN

    def pre_start(self):
        self.access_manager.register_access_level("superadmin", 10, self.check_superadmin)
        self.event_manager.register_event_type("connect")
        self.event_manager.register_event_type("packet")

    def start(self):
        self.setting_manager.register("org_channel_max_page_length", 7500, "Maximum size of blobs in org channel",
                                      NumberSettingType([4500, 6000, 7500, 9000, 10500, 12000]), "core.system")
        self.setting_manager.register("private_message_max_page_length", 7500, "Maximum size of blobs in private messages",
                                      NumberSettingType([4500, 6000, 7500, 9000, 10500, 12000]), "core.system",)
        self.setting_manager.register("private_channel_max_page_length", 7500, "Maximum size of blobs in private channel",
                                      NumberSettingType([4500, 6000, 7500, 9000, 10500, 12000]), "core.system")
        self.setting_manager.register("header_color", "#FFFF00", "color for headers", ColorSettingType(), "core.colors")
        self.setting_manager.register("header2_color", "#FCA712", "color for sub-headers", ColorSettingType(), "core.colors")
        self.setting_manager.register("highlight_color", "#FFFFFF", "color for highlight", ColorSettingType(), "core.colors")
        self.setting_manager.register("neutral_color", "#E6E1A6", "color for neutral faction", ColorSettingType(), "core.colors")
        self.setting_manager.register("omni_color", "#FA8484", "color for omni faction", ColorSettingType(), "core.colors")
        self.setting_manager.register("clan_color", "#F79410", "color for clan faction", ColorSettingType(), "core.colors")
        self.setting_manager.register("unknown_color", "#FF0000", "color for unknown faction", ColorSettingType(), "core.colors")
        self.setting_manager.register("notice_color", "#FF8C00", "color for important notices", ColorSettingType(), "core.colors")
        self.setting_manager.register("symbol", "!", "Symbol for executing bot commands", TextSettingType(["!", "#", "*", "@", "$", "+", "-"]), "core.system")

    def check_superadmin(self, char_id):
        char_name = self.character_manager.resolve_char_to_name(char_id)
        return char_name == self.superadmin

    def run(self):
        while None is not self.iterate():
            pass

        self.event_manager.fire_event("connect", None)
        self.ready = True

        while self.status == BotStatus.RUN:
            try:
                timestamp = int(time.time())

                # timer events will execute not more often than once per second
                if self.last_timer_event < timestamp:
                    self.last_timer_event = timestamp
                    self.job_scheduler.check_for_scheduled_jobs(timestamp)
                    self.event_manager.check_for_timer_events(timestamp)

                self.iterate()
            except Exception as e:
                self.logger.error("", e)

        return self.status

    def add_packet_handler(self, packet_id, handler):
        handlers = self.packet_handlers.get(packet_id, [])
        handlers.append(handler)
        self.packet_handlers[packet_id] = handlers

    def iterate(self):
        packet = self.read_packet()
        if packet:
            if isinstance(packet, server_packets.PrivateMessage):
                self.handle_private_message(packet)
            elif isinstance(packet, server_packets.PublicChannelJoined):
                # set org id and org name
                if packet.channel_id >> 32 == 3:
                    self.org_id = 0x00ffffffff & packet.channel_id
                    if packet.name != "Clan (name unknown)":
                        self.org_name = packet.name
            elif isinstance(packet, server_packets.SystemMessage):
                try:
                    category_id = 20000
                    instance_id = packet.message_id
                    template = self.mmdb_parser.get_message_string(category_id, instance_id)
                    params = self.mmdb_parser.parse_params(packet.message_args)
                    packet.extended_message = ExtendedMessage(category_id, instance_id, template, params)
                    self.logger.log_chat("SystemMessage", None, packet.extended_message.get_message())
                except Exception as e:
                    self.logger.error("", e)
            elif isinstance(packet, server_packets.PublicChannelMessage):
                msg = packet.message
                if msg.startswith("~&") and msg.endswith("~"):
                    msg = msg[2:-1]
                    try:
                        category_id = self.mmdb_parser.read_base_85(msg[0:5])
                        instance_id = self.mmdb_parser.read_base_85(msg[5: 10])
                        template = self.mmdb_parser.get_message_string(category_id, instance_id)
                        params = self.mmdb_parser.parse_params(msg[10:])
                        packet.extended_message = ExtendedMessage(category_id, instance_id, template, params)
                    except Exception as e:
                        self.logger.error("", e)

            for handler in self.packet_handlers.get(packet.id, []):
                handler(packet)

            self.event_manager.fire_event("packet:" + str(packet.id), packet)

        # check packet queue for outgoing packets
        outgoing_packet = self.packet_queue.dequeue()
        while outgoing_packet:
            self.send_packet(outgoing_packet)
            outgoing_packet = self.packet_queue.dequeue()

        return packet

    def send_org_message(self, msg):
        org_channel_id = self.public_channel_manager.org_channel_id
        if org_channel_id is None:
            self.logger.warning("Could not send message to org channel, unknown org id")
        else:
            for page in self.get_text_pages(msg, self.setting_manager.get("org_channel_max_page_length").get_value()):
                packet = client_packets.PublicChannelMessage(org_channel_id, page, "")
                # self.send_packet(packet)
                self.packet_queue.enqueue(packet)

    def send_private_message(self, char, msg):
        char_id = self.character_manager.resolve_char_to_id(char)
        if char_id is None:
            self.logger.warning("Could not send message to %s, could not find char id" % char)
        else:
            for page in self.get_text_pages(msg, self.setting_manager.get("private_message_max_page_length").get_value()):
                self.logger.log_tell("To", self.character_manager.get_char_name(char_id), page)
                packet = client_packets.PrivateMessage(char_id, page, "\0")
                # self.send_packet(packet)
                self.packet_queue.enqueue(packet)

    def send_private_channel_message(self, msg, private_channel=None):
        if private_channel is None:
            private_channel = self.char_id

        private_channel_id = self.character_manager.resolve_char_to_id(private_channel)
        if private_channel_id is None:
            self.logger.warning("Could not send message to private channel %s, could not find private channel" % private_channel)
        else:
            for page in self.get_text_pages(msg, self.setting_manager.get("private_channel_max_page_length").get_value()):
                packet = client_packets.PrivateChannelMessage(private_channel_id, page, "\0")
                self.send_packet(packet)

    def handle_private_message(self, packet: server_packets.PrivateMessage):
        self.logger.log_tell("From", self.character_manager.get_char_name(packet.char_id), packet.message)

    def handle_public_channel_message(self, packet: server_packets.PublicChannelMessage):
        self.logger.log_chat(
            self.public_channel_manager.get_channel_name(packet.channel_id),
            self.character_manager.get_char_name(packet.char_id),
            packet.message)

    def get_text_pages(self, msg, max_page_length):
        if isinstance(msg, ChatBlob):
            return self.text.paginate(msg.title, msg.msg, max_page_length, msg.max_num_pages, msg.footer)
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
