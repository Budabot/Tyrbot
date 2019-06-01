from core.chat_blob import ChatBlob
from core.decorators import instance, event, setting
from core.logger import Logger
from core.private_channel_service import PrivateChannelService
from core.public_channel_service import PublicChannelService
from core.setting_types import BooleanSettingType
from core.tyrbot import Tyrbot


@instance()
class OrgChannelController:
    PRIVATE_CHANNEL_PREFIX = "[Private]"
    ORG_CHANNEL_PREFIX = "[Org]"

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.setting_service = registry.get_instance("setting_service")
        self.text = registry.get_instance("text")
        self.pork_service = registry.get_instance("pork_service")
        self.character_service = registry.get_instance("character_service")
        self.alts_service = registry.get_instance("alts_service")
        self.alts_controller = registry.get_instance("alts_controller")

    @setting(name="private_channel_relay_commands", value="True", description="Relay commands and command output to and from private channel")
    def private_channel_relay_commands(self):
        return BooleanSettingType()

    @event(event_type=PublicChannelService.ORG_CHANNEL_MESSAGE_EVENT, description="Relay messages from the org channel to the private channel")
    def handle_org_message_event(self, event_type, event_data):
        if event_data.char_id != self.bot.char_id:
            if event_data.message[0] != self.setting_service.get("symbol").get_value() or self.private_channel_relay_commands().get_value():
                if event_data.extended_message:
                    message = event_data.extended_message.get_message()
                else:
                    message = event_data.message

                if event_data.char_id == 4294967295 or event_data.char_id == 0:
                    self.bot.send_private_channel_message("%s: %s" % (self.ORG_CHANNEL_PREFIX, message), fire_outgoing_event=False)
                else:
                    char_name = self.character_service.resolve_char_to_name(event_data.char_id)
                    self.bot.send_private_channel_message("%s %s: %s" % (self.ORG_CHANNEL_PREFIX, char_name, message), fire_outgoing_event=False)

    @event(event_type=PrivateChannelService.PRIVATE_CHANNEL_MESSAGE_EVENT, description="Relay messages from the private channel to the org channel")
    def handle_private_channel_message_event(self, event_type, event_data):
        if event_data.char_id != self.bot.char_id:
            if event_data.message[0] != self.setting_service.get("symbol").get_value() or self.private_channel_relay_commands().get_value():
                char_name = self.character_service.resolve_char_to_name(event_data.char_id)
                self.bot.send_org_message("%s %s: %s" % (self.PRIVATE_CHANNEL_PREFIX, char_name, event_data.message), fire_outgoing_event=False)

    @event(event_type=Tyrbot.OUTGOING_PRIVATE_CHANNEL_MESSAGE_EVENT, description="Relay commands from the private channel to the org channel")
    def outgoing_private_channel_message_event(self, event_type, event_data):
        self.bot.send_org_message(self.add_page_prefix(event_data.message, self.PRIVATE_CHANNEL_PREFIX), fire_outgoing_event=False)

    @event(event_type=Tyrbot.OUTGOING_ORG_MESSAGE_EVENT, description="Relay commands from the org channel to the private channel")
    def outgoing_org_message_event(self, event_type, event_data):
        self.bot.send_private_channel_message(self.add_page_prefix(event_data.message, self.ORG_CHANNEL_PREFIX), fire_outgoing_event=False)

    def add_page_prefix(self, msg, prefix):
        if isinstance(msg, ChatBlob):
            msg.page_prefix = prefix + " "
        else:
            msg = prefix + " " + msg

        return msg
