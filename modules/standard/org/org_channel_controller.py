from core.decorators import instance, event, timerevent
from core.logger import Logger
from core.private_channel_service import PrivateChannelService
from core.public_channel_service import PublicChannelService


@instance()
class OrgChannelController:
    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.setting_service = registry.get_instance("setting_service")

    @event(event_type=PublicChannelService.ORG_MESSAGE_EVENT, description="Relay messages from the org channel to the private channel")
    def handle_org_message_event(self, event_type, event_data):
        if event_data.char_id != self.bot.char_id and event_data.message[0] != self.setting_service.get("symbol").get_value():
            self.bot.send_private_channel_message(event_data.message)

    @event(event_type=PrivateChannelService.PRIVATE_CHANNEL_MESSAGE_EVENT, description="Relay messages from the private channel to the org channel")
    def handle_private_channel_message_event(self, event_type, event_data):
        if event_data.char_id != self.bot.char_id and event_data.message[0] != self.setting_service.get("symbol").get_value():
            self.bot.send_org_message(event_data.message)
