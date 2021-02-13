from core.aochat import server_packets, client_packets
from core.conn import Conn
from core.decorators import instance
from core.logger import Logger
from core.lookup.character_service import CharacterService
from core.setting_service import SettingService
from core.setting_types import BooleanSettingType
from core.tyrbot import Tyrbot
import re


@instance("Darknet")
class DarkController:
    relay_channel_id = None
    relay_name = None
    MESSAGE_SOURCE = "darknet"
    message_regex = re.compile(r"^(<font color='#\S+'>){2}\[([a-zA-Z]{2,})\]<\/font> <font color='#\S+'>(.+)<\/font> <font color='#\S+'>\[(.+)\]<\/font> \[(.+)\]$", re.DOTALL)

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot: Tyrbot = registry.get_instance("bot")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.message_hub_service = registry.get_instance("message_hub_service")

    def pre_start(self):
        self.bot.register_packet_handler(server_packets.PrivateChannelInvited.id, self.handle_private_channel_invite, 50)
        self.bot.register_packet_handler(server_packets.PrivateChannelMessage.id, self.handle_private_channel_message)
        self.message_hub_service.register_message_source(self.MESSAGE_SOURCE)

    def start(self):
        self.setting_service.register(self.module_name, "dark_relay", "false", BooleanSettingType(), "Is the Module Enabled?")
        self.setting_service.register(self.module_name, "dark_wts", "true", BooleanSettingType(), "Is the WTS channel visible?")
        self.setting_service.register(self.module_name, "dark_wtb", "true", BooleanSettingType(), "Is the WTB channel visible?")
        self.setting_service.register(self.module_name, "dark_lr", "true", BooleanSettingType(), "Is the Lootrights channel visible?")
        self.setting_service.register(self.module_name, "dark_gen", "true", BooleanSettingType(), "Is the General channel visible?")
        self.setting_service.register(self.module_name, "dark_pvp", "true", BooleanSettingType(), "Is the PvP channel visible?")
        self.setting_service.register(self.module_name, "dark_pvm", "true", BooleanSettingType(), "Is the PVM channel visible?")
        self.setting_service.register(self.module_name, "dark_event", "true", BooleanSettingType(), "Is the Event channel visible?")

    def handle_private_channel_invite(self, conn: Conn, packet: server_packets.PrivateChannelInvited):
        if not conn.is_main:
            pass

        if self.setting_service.get_value("dark_relay") == "0":
            return

        if "Darknet" == self.character_service.get_char_name(packet.private_channel_id):
            channel_name = self.character_service.get_char_name(packet.private_channel_id)
            conn.send_packet(client_packets.PrivateChannelJoin(packet.private_channel_id))
            self.logger.info("Joined private channel {channel}".format(channel=channel_name))
            self.relay_channel_id = packet.private_channel_id
            self.relay_name = channel_name

    def handle_private_channel_message(self, conn, packet: server_packets.PrivateChannelMessage):
        if not conn.is_main:
            pass

        if self.setting_service.get_value("dark_relay") == "0":
            return

        if packet.private_channel_id == self.relay_channel_id:
            if self.bot.get_char_id() == packet.char_id:
                return
            if packet.char_id != self.relay_channel_id:
                return
            channel_name = self.character_service.get_char_name(packet.private_channel_id)
            char_name = self.character_service.get_char_name(packet.char_id)
            self.logger.log_chat(conn.id, "Private Channel(%s)" % channel_name, char_name, packet.message)
            message = packet.message.lstrip()
            self.processIncomingRelayMessage(message)

    def processIncomingRelayMessage(self, message):
        if re.search(self.message_regex, message):
            cont = re.findall(self.message_regex, message)
            cont = cont[0]
            ch = cont[1].lower()
            msg = cont[2]
            tell = cont[3]
            report = cont[4]
            if ch == "wts":
                if self.setting_service.get_value("dark_wts") == "0":
                    return
                channel = "<red>WTS</red>"
            elif ch == "wtb":
                if self.setting_service.get_value("dark_wtb") == "0":
                    return
                channel = "<green>WTB</green>"
            elif ch == "lootrights":
                if self.setting_service.get_value("dark_lr") == "0":
                    return
                channel = "<violet>LR<(violet)>"
            elif ch == "general":
                if self.setting_service.get_value("dark_gen") == "0":
                    return
                channel = "<notice>Gen</notice>"
            elif ch == "pvm":
                if self.setting_service.get_value("dark_pvm") == "0":
                    return
                channel = "<cyan>PvM</cyan>"
            elif ch == "event":
                if self.setting_service.get_value("dark_event") == "0":
                    return
                channel = "<highlight>Event</highlight>"
            elif ch == "pvp":
                if self.setting_service.get_value("dark_pvp") == "0":
                    return
                channel = "<grey>PvP</grey>"
            elif ch == "auction":
                channel = "<yellow>AUCTION</yellow>"
            else:
                return

            message = ("[%s] <orange>%s<end> [%s] [%s]" % (channel, msg, tell, report))
            self.message_hub_service.send_message(self.MESSAGE_SOURCE, None, None, message)