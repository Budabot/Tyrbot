from core.decorators import instance, event, timerevent
from core.logger import Logger
from core.private_channel_service import PrivateChannelService
from core.public_channel_service import PublicChannelService
from modules.core.org_members.org_member_controller import OrgMemberController


@instance()
class OrgChannelController:
    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.setting_service = registry.get_instance("setting_service")
        self.text = registry.get_instance("text")
        self.pork_service = registry.get_instance("pork_service")
        self.character_service = registry.get_instance("character_service")

    @event(event_type=PublicChannelService.ORG_MESSAGE_EVENT, description="Relay messages from the org channel to the private channel")
    def handle_org_message_event(self, event_type, event_data):
        if event_data.char_id != self.bot.char_id and event_data.message[0] != self.setting_service.get("symbol").get_value():
            self.bot.send_private_channel_message(event_data.message)

    @event(event_type=PrivateChannelService.PRIVATE_CHANNEL_MESSAGE_EVENT, description="Relay messages from the private channel to the org channel")
    def handle_private_channel_message_event(self, event_type, event_data):
        if event_data.char_id != self.bot.char_id and event_data.message[0] != self.setting_service.get("symbol").get_value():
            self.bot.send_org_message(event_data.message)

    @event(OrgMemberController.ORG_MEMBER_LOGON_EVENT, "Notify when org member logs on")
    def org_member_logon_event(self, event_type, event_data):
        if self.bot.is_ready():
            char_info = self.pork_service.get_character_info(event_data.char_id)
            if char_info:
                self.bot.send_org_message("%s has logged on." % self.text.format_char_info(char_info))
            else:
                char_name = self.character_service.resolve_char_to_name(event_data.char_id)
                self.bot.send_org_message("<highlight>%s<end> has logged on." % char_name)

    @event(OrgMemberController.ORG_MEMBER_LOGOFF_EVENT, "Notify when org member logs off")
    def org_member_logoff_event(self, event_type, event_data):
        if self.bot.is_ready():
            char_name = self.character_service.resolve_char_to_name(event_data.char_id)
            self.bot.send_org_message("<highlight>%s<end> has logged off." % char_name)
