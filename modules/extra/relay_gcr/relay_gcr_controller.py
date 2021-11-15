import re
import time

from core.aochat import server_packets, client_packets
from core.db import DB
from core.decorators import instance, event, command
from core.logger import Logger
from core.lookup.character_service import CharacterService
from core.public_channel_service import PublicChannelService
from core.setting_service import SettingService
from core.setting_types import TextSettingType, BooleanSettingType, ColorSettingType
from core.tyrbot import Tyrbot
from core.private_channel_service import PrivateChannelService
from modules.core.org_members.org_member_controller import OrgMemberController
from modules.standard.online.online_controller import OnlineController
from core.command_param_types import Any


#
#   Custom written by Bitnykk/Kynethic courtesy of Minidodo (Cyndergames.at) aka Idande/Cildie.
#   Thanks Tyrence that helped to update for newest Tyrbot ; install into modules/custom folder.
#
@instance()
class RelayGcrController:
    relay_channel_id = None
    relay_name = None
    org = None

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot: Tyrbot = registry.get_instance("bot")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.public_channel_service: PublicChannelService = registry.get_instance("public_channel_service")
        self.db: DB = registry.get_instance("db")
        self.character_service = registry.get_instance("character_service")
        self.online_controller = registry.get_instance("online_controller")
        self.pork_service = registry.get_instance("pork_service")

    def start(self):
        self.setting_service.register(self.module_name, "relaygcr_type", "private_channel", TextSettingType(["tell", "private_channel"]), "Type of relay")
        self.setting_service.register(self.module_name, "relaygcr_symbol", "@", TextSettingType(["!", "#", "*", "@", "$", "+", "-"]), "Symbol for external relay")
        self.setting_service.register(self.module_name, "relaygcr_symbol_method", "with_symbol", TextSettingType(["Always", "with_symbol", "unless_symbol"]), "When to relay messages")
        self.setting_service.register(self.module_name, "relaygcr_bot", "Relay", TextSettingType(), "Bot for Guildrelay")
        self.setting_service.register(self.module_name, "relaygcr_enabled", False, BooleanSettingType(), "Is the Module Enabled?")
        self.setting_service.register(self.module_name, "relaygcr_color_guild", "#C3C3C3", ColorSettingType(), "Color of messages from relay to guild channel")
        self.setting_service.register(self.module_name, "relaygcr_color_priv", "#C3C3C3", ColorSettingType(), "Color of messages from relay to priv channel")
        self.setting_service.register(self.module_name, "relaygcr_guest", False, BooleanSettingType(), "Relay the Private/Guest Channel")
        self.setting_service.register(self.module_name, "relaygcr_guild_abbreviation", "ORG_TAG", TextSettingType(), "Abbreviation to use for org name")
        self.setting_service.register(self.module_name, "relaygcr_share", False, BooleanSettingType(), "Do we share online lists with relayed partners?")
        self.setting_service.register(self.module_name, "relaygcr_others", "", TextSettingType(allow_empty=True), "Online wanted Bot(s) unspaced list ; separated (example: Bot1;Bot2;Bot3)")

        self.bot.register_packet_handler(server_packets.PrivateChannelInvited.id, self.handle_private_channel_invite)
        self.bot.register_packet_handler(server_packets.PrivateChannelMessage.id, self.handle_private_channel_message)
        self.bot.register_packet_handler(server_packets.PublicChannelMessage.id, self.handle_org_channel_message)

    def handle_private_channel_invite(self, conn, packet: server_packets.PrivateChannelInvited):
        channel_name = self.character_service.get_char_name(packet.private_channel_id)

        if self.setting_service.get_value("relaygcr_enabled") == "0":
            self.logger.info(f"Denied private Channel invite: {channel_name} - Relay Module not active")
        elif self.setting_service.get_value("relaygcr_bot") != channel_name:
            self.logger.info(f"Denied private Channel invite: {channel_name} - not the Relaybot")
        else:
            conn.send_packet(client_packets.PrivateChannelJoin(packet.private_channel_id))
            self.logger.info(f"Joined private channel {channel_name}")
            self.relay_channel_id = packet.private_channel_id
            self.relay_name = channel_name
            self.online_send()
            self.send("!gcrc onlinereq")

    def handle_private_channel_message(self, conn, packet: server_packets.PrivateChannelMessage):
        if self.setting_service.get_value("relaygcr_enabled") == "0":
            return

        if packet.private_channel_id != conn.char_id:
            if conn.char_id == packet.char_id:
                return

            if len(packet.message) < 2:
                return

            channel_name = self.character_service.get_char_name(packet.private_channel_id)
            char_name = self.character_service.get_char_name(packet.char_id)
            message = packet.message.lstrip()

            self.process_incoming_relay_message(channel_name, char_name, message)
        elif packet.private_channel_id == conn.char_id and self.setting_service.get_value("relaygcr_guest") == "1":
            self.process_outgoing_relay_message(packet, conn)

    def handle_org_channel_message(self, conn, packet: server_packets.PublicChannelMessage):
        if self.setting_service.get_value("relaygcr_enabled") == "0":
            return

        if self.public_channel_service.is_org_channel_id(packet.channel_id) and packet.char_id != conn.char_id:
            self.process_outgoing_relay_message(packet, conn)

    @event(event_type="connect", description="Initialize online with relay tell partner", is_enabled=True)
    def connect_event(self, event_type, event_data):
        if self.setting_service.get_value("relaygcr_share") == "1" and self.setting_service.get_value("relaygcr_type") == "tell":
            self.relay_name = self.setting_service.get_value("relaygcr_bot")
            self.online_send()
            self.send("!gcrc onlinereq")

    @event(event_type=PrivateChannelService.JOINED_PRIVATE_CHANNEL_EVENT, description="Send to relay when someone joins private channel", is_enabled=True)
    def private_channel_joined_event(self, event_type, event_data):
        if self.setting_service.get_value("relaygcr_share") == "1":
            name = self.character_service.resolve_char_to_name(event_data.char_id)
            self.send("!gcrc buddy 1 " + name + " pg 0")

    @event(event_type=PrivateChannelService.LEFT_PRIVATE_CHANNEL_EVENT, description="Send to relay when someone joins private channel", is_enabled=True)
    def private_channel_left_event(self, event_type, event_data):
        if self.setting_service.get_value("relaygcr_share") == "1":
            name = self.character_service.resolve_char_to_name(event_data.char_id)
            self.send("!gcrc buddy 0 " + name + " pg 0")

    @event(event_type=OrgMemberController.ORG_MEMBER_LOGON_EVENT, description="Send to relay when org member logs on", is_enabled=True)
    def org_member_logon_event(self, event_type, event_data):
        if self.setting_service.get_value("relaygcr_share") == "1":
            name = self.character_service.resolve_char_to_name(event_data.char_id)
            self.send("!gcrc buddy 1 " + name + " gc 0")

    @event(event_type=OrgMemberController.ORG_MEMBER_LOGOFF_EVENT, description="Send to relay when org member logs off", is_enabled=True)
    def org_member_logoff_event(self, event_type, event_data):
        if self.setting_service.get_value("relaygcr_share") == "1":
            name = self.character_service.resolve_char_to_name(event_data.char_id)
            self.send("!gcrc buddy 0 " + name + " gc 0")

    @command(command="gcr", params=[Any("msg")], description="Incoming gcr tells", access_level="all")
    def gcr_inc_tell(self, request, msg):
        name = self.character_service.resolve_char_to_name(request.sender.char_id)
        self.process_incoming_relay_message(name, name, "!gcr " + msg)

    @command(command="gcrc", params=[Any("msg")], description="Incoming gcrc tells", access_level="all")
    def gcrc_inc_tell(self, request, msg):
        name = self.character_service.resolve_char_to_name(request.sender.char_id)
        self.process_incoming_relay_message(name, name, "!gcrc " + msg)

    def process_incoming_relay_message(self, channel, sender, message):
        if self.setting_service.get_value("relaygcr_enabled") == "0":
            return

        if message[:5] == "!gcrc" and self.setting_service.get_value("relaygcr_share") == "1":
            message = message[6:]
            others = self.setting_service.get_value("relaygcr_others")
            if len(others) > 0:
                bots = others.split(";")
                t = int(time.time())
                for bot in bots:
                    if bot.capitalize() == sender:
                        self.online_controller.register_online_channel(sender)
                        if message[:9] == "onlinereq":
                            self.online_send()
                        elif message[:6] == "online":
                            message = message[7:]
                            onliners = message.split(";")
                            self.db.exec("DELETE FROM online WHERE channel = ?", [sender])
                            for onliner in onliners:
                                info = onliner.split(",")
                                self.add_to_online(sender, info[0], t)
                        elif message[:5] == "buddy":
                            message = message[6:]
                            info = message.split(" ")
                            if info[0] == "0":
                                char_id = self.character_service.resolve_char_to_id(info[1])
                                self.db.exec("DELETE FROM online WHERE char_id = ?", [char_id])
                            elif info[0] == "1":
                                self.add_to_online(sender, info[1], t)
        elif message[:4] == "!gcr":
            message = message[5:]
            message = message.replace("##relay_channel##", "")
            message = re.sub(r'##relay_name##([^:]+):##end##', r'<a href="user://\1">\1</a>:', message)
            message = message.replace("##relay_name##", "")
            colorom = self.setting_service.get_value("relaygcr_color_guild")
            messago = re.sub(r'##relay_message##([^#]+)##end##', r'<font color="{color}">\1</font>'.format(color=colorom), message)
            messago = messago.replace("##end##", "")
            colorpm = self.setting_service.get_value("relaygcr_color_priv")
            messagp = re.sub(r'##relay_message##([^#]+)##end##', r'<font color="{color}">\1</font>'.format(color=colorpm), message)
            messagp = messagp.replace("##end##", "")
            if channel == self.setting_service.get_value("relaygcr_bot"):
                self.bot.send_org_message(messago)
                if self.setting_service.get_value("relaygcr_guest") == "1":
                    self.bot.send_private_channel_message(messagp)

    def process_outgoing_relay_message(self, packet, conn):
        if self.setting_service.get_value("relaygcr_enabled") == "0":
            return

        if packet.char_id == conn.char_id:
            return

        method = self.setting_service.get_value("relaygcr_symbol_method")
        sender = self.character_service.get_char_name(packet.char_id)

        plain_msg = packet.message
        symbol = self.setting_service.get_value("relaygcr_symbol")
        # TODO handle when not set
        org = self.setting_service.get_value("relaygcr_guild_abbreviation")
        msg = None
        if method == "Always":
            msg = "!gcr [##relay_channel##{org}##end##] ##relay_name##{char}:##end## ##relay_message##{msg}##end##".format(org=org, char=sender, msg=plain_msg)
        elif method == "with_symbol":
            if plain_msg[:len(symbol)] == symbol:
                msg = "!gcr [##relay_channel##{org}##end##] ##relay_name##{char}:##end## ##relay_message##{msg}##end##".format(org=org, char=sender, msg=plain_msg[len(symbol):])
        elif method == "unless_symbol":
            if plain_msg[:len(symbol)] != symbol:
                msg = "!gcr [##relay_channel##{org}##end##] ##relay_name##{char}:##end## ##relay_message##{msg}##end##".format(org=org, char=sender, msg=plain_msg)
        self.send(msg)

    def send(self, msg):
        if not msg:
            return

        if self.setting_service.get_value("relaygcr_type") == "private_channel":
            if self.relay_channel_id:
                self.bot.send_private_channel_message(private_channel_id=self.relay_channel_id, msg=msg, add_color=False)
            else:
                self.logger.info("Not a member of a relay, ignoring message")
        else:
            self.bot.send_private_message(char_id=self.character_service.resolve_char_to_id(self.relay_name), msg=msg)

    def online_send(self):
        blob = "!gcrc online "
        sql = "SELECT char_id as id, channel as ch FROM online WHERE (channel = ? OR channel = ?)"
        data = self.db.query(sql, [OnlineController.ORG_CHANNEL, OnlineController.PRIVATE_CHANNEL])
        for char in data:
            name = self.character_service.resolve_char_to_name(char.id)
            if char.ch == "Org":
                blob += name + ",gc,0;"
            else:
                blob += name + ",pg,0;"
        blob = blob[:-1]
        self.send(blob)

    def add_to_online(self, sender, name, t):
        char_id = self.character_service.resolve_char_to_id(name)
        self.pork_service.load_character_info(char_id, name)

        sql = "SELECT 1 FROM online WHERE char_id = ? LIMIT 1"
        check = self.db.query_single(sql, [char_id])
        if not check:
            self.db.exec("INSERT INTO online (char_id, afk_dt, afk_reason, channel, dt) VALUES (?, ?, ?, ?, ?)", [char_id, 0, "", sender, t])
