from core.aochat import server_packets, client_packets
from core.decorators import instance
from core.logger import Logger
from core.lookup.character_service import CharacterService
from core.setting_service import SettingService
from core.setting_types import TextSettingType, BooleanSettingType, ColorSettingType
from core.tyrbot import Tyrbot


@instance("AllianceRelayController")
class AllianceRelayController:
    relay_channel_id = None
    MESSAGE_SOURCE = "alliance"

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot: Tyrbot = registry.get_instance("bot")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.message_hub_service = registry.get_instance("message_hub_service")
        self.public_channel_service = registry.get_instance("public_channel_service")

    def pre_start(self):
        self.message_hub_service.register_message_source(self.MESSAGE_SOURCE)

    def start(self):
        self.setting_service.register("arelay_symbol", "#", "Symbol for external relay",
                                      TextSettingType(["!", "#", "*", "@", "$", "+", "-"]), "custom.arelay")
        self.setting_service.register("arelay_symbol_method", "with_symbol", "When to relay messages",
                                      TextSettingType(["Always", "with_symbol", "unless_symbol"]), "custom.arelay")
        self.setting_service.register("arelaybot", "", "Bot for alliance relay", TextSettingType(allow_empty=True), "custom.arelay")
        self.setting_service.register("arelay_enabled", False, "Enable the alliance relay", BooleanSettingType(),
                                      "custom.arelay")
        self.setting_service.register("arelay_guild_abbreviation", "", "Abbreviation to use for org name",
                                      TextSettingType(allow_empty=True), "custom.arelay")
        self.setting_service.register("arelay_color", "#C3C3C3", "Color of messages from relay",
                                      ColorSettingType(), "custom.arelay")

        self.message_hub_service.register_message_destination(self.MESSAGE_SOURCE,
                                                              self.handle_relay_hub_message,
                                                              ["org_channel"],
                                                              [self.MESSAGE_SOURCE])

        self.bot.add_packet_handler(server_packets.PrivateChannelInvited.id, self.handle_private_channel_invite, 100)
        self.bot.add_packet_handler(server_packets.PrivateChannelMessage.id, self.handle_private_channel_message)

    def handle_private_channel_invite(self, packet: server_packets.PrivateChannelInvited):
        if not self.setting_service.get("arelay_enabled").get_value():
            return

        channel_name = self.character_service.get_char_name(packet.private_channel_id)
        if self.setting_service.get_value("arelaybot").lower() == channel_name.lower():
            self.bot.send_packet(client_packets.PrivateChannelJoin(packet.private_channel_id))
            self.logger.info("Joined private channel {channel}".format(channel=channel_name))
            self.relay_channel_id = packet.private_channel_id

    def handle_private_channel_message(self, packet: server_packets.PrivateChannelMessage):
        if not self.setting_service.get("arelay_enabled").get_value():
            return

        # ignore packets from the bot's own private channel and from the bot itself
        if packet.private_channel_id == self.bot.char_id or packet.char_id == self.bot.char_id:
            return

        message = packet.message.lstrip()
        if message[:6] != "!agcr ":
            return

        message = message[6:]
        formatted_message = "{color}{msg}</font>" \
            .format(color=self.setting_service.get("arelay_color").get_font_color(),
                    msg=message)

        # sender is not the bot that sent it, but rather the original char that sent the message
        # given the format of !agcr messages, it could be possible to parse the sender for the message
        # but currently this is not done
        sender = None

        self.message_hub_service.send_message(self.MESSAGE_SOURCE, sender, None, formatted_message)

    def handle_relay_hub_message(self, ctx):
        if not self.setting_service.get("arelay_enabled").get_value():
            return

        method = self.setting_service.get_value("arelay_symbol_method")
        symbol = self.setting_service.get_value("arelay_symbol")
        plain_msg = ctx.message

        if method == "unless_symbol" and len(plain_msg) > len(symbol) and plain_msg[:len(symbol)] == symbol:
            return
        elif method == "with_symbol":
            if len(plain_msg) < len(symbol) or plain_msg[:len(symbol)] != symbol:
                return
            else:
                # trim symbol from message
                plain_msg = plain_msg[len(symbol):]

        org = self.setting_service.get_value("arelay_guild_abbreviation") or \
              self.public_channel_service.get_org_name() or \
              self.bot.char_name
        msg = "[{org}] {char}: {msg}".format(org=org, char=ctx.sender.name, msg=plain_msg)

        self.send_message_to_alliance(msg)

    def send_message_to_alliance(self, msg):
        if self.relay_channel_id:
            self.bot.send_private_channel_message(private_channel=self.relay_channel_id,
                                                  msg="!agcr " + msg, fire_outgoing_event=False, add_color=False)
