from core.decorators import instance, event
from core.dict_object import DictObject
from core.logger import Logger
from core.public_channel_service import PublicChannelService


@instance()
class OrgChannelController:
    RELAY_CHANNEL_PREFIX = "[Org]"
    RELAY_HUB_SOURCE = "org_channel"

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.character_service = registry.get_instance("character_service")
        self.relay_hub_service = registry.get_instance("relay_hub_service")
        self.ban_service = registry.get_instance("ban_service")

    def start(self):
        self.relay_hub_service.register_relay(self.RELAY_HUB_SOURCE, self.handle_incoming_relay_message)

    def handle_incoming_relay_message(self, ctx):
        message = ctx.message

        self.bot.send_org_message(message, fire_outgoing_event=False)

    @event(event_type=PublicChannelService.ORG_CHANNEL_MESSAGE_EVENT, description="Relay messages from the org channel to the relay hub", is_hidden=True)
    def handle_org_message_event(self, event_type, event_data):
        if event_data.char_id == self.bot.char_id or self.ban_service.get_ban(event_data.char_id):
            return

        if event_data.extended_message:
            message = event_data.extended_message.get_message()
        else:
            message = event_data.message

        sender = None
        if event_data.char_id == 4294967295 or event_data.char_id == 0:
            message = "%s: %s" % (self.RELAY_CHANNEL_PREFIX, message)
        else:
            char_name = self.character_service.resolve_char_to_name(event_data.char_id)
            sender = DictObject({"char_id": event_data.char_id, "name": char_name})
            message = "%s %s: %s" % (self.RELAY_CHANNEL_PREFIX, char_name, message)

        self.relay_hub_service.send_message(self.RELAY_HUB_SOURCE, sender, message)
