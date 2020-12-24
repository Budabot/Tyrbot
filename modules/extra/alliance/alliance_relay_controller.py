from core.aochat import server_packets, client_packets
from core.decorators import instance
from core.logger import Logger
from core.lookup.character_service import CharacterService
from core.setting_service import SettingService
from core.setting_types import TextSettingType, BooleanSettingType
from core.tyrbot import Tyrbot


@instance("AllianceRelayController")
class AllianceRelayController:
    relay_channel_id = None
    RELAY_HUB_SOURCE = "alliance"

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot: Tyrbot = registry.get_instance("bot")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.relay_hub_service = registry.get_instance("relay_hub_service")

    def start(self):
        self.setting_service.register("arelay_symbol", "#", "Symbol for external relay",
                                      TextSettingType(["!", "#", "*", "@", "$", "+", "-"]), "custom.arelay")
        self.setting_service.register("arelay_symbol_method", "Always", "When to relay messages",
                                      TextSettingType(["Always", "with_symbol", "unless_symbol"]), "custom.arelay")
        self.setting_service.register("arelaybot", "", "Bot for alliance relay", TextSettingType([]), "custom.arelay")
        self.setting_service.register("arelay_enabled", False, "Enable the alliance relay", BooleanSettingType(),
                                      "custom.arelay")
        self.setting_service.register("arelay_guild_abbreviation", "", "Abbreviation to use for org name",
                                      TextSettingType([]), "custom.arelay")

        self.relay_hub_service.register_relay(self.RELAY_HUB_SOURCE, self.handle_relay_hub_message)

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

        # sender is not the bot that sent it, but rather the original char that sent the message
        # given the format of !agcr messages, it could be possible to parse the sender for the message
        # but currently this is not done
        sender = None

        self.relay_hub_service.send_message(self.RELAY_HUB_SOURCE, sender, None, message)

    def handle_relay_hub_message(self, ctx):
        if not self.setting_service.get("arelay_enabled").get_value():
            return

        method = self.setting_service.get_value("arelay_symbol_method")
        symbol = self.setting_service.get_value("arelay_symbol")
        plain_msg = ctx.message

        if method == "unless_symbol" and len(plain_msg) > len(symbol) and plain_msg[:len(symbol)] == symbol:
            return
        elif method == "with_symbol":
            if len(plain_msg) > len(symbol) and plain_msg[:len(symbol)] != symbol:
                return
            else:
                # trim symbol from message
                plain_msg = plain_msg[len(symbol):]

        org = self.setting_service.get_value("arelay_guild_abbreviation")
        msg = "[{org}] {char}: {msg}".format(org=org, char=ctx.sender.name, msg=plain_msg)

        self.send_message_to_alliance(msg)

    def send_message_to_alliance(self, msg):
        if self.relay_channel_id:
            self.bot.send_private_channel_message(private_channel=self.relay_channel_id,
                                                  msg="!agcr " + msg, fire_outgoing_event=False, add_color=False)
