from core.decorators import instance, event, timerevent, setting
from core.logger import Logger
from core.private_channel_service import PrivateChannelService
from core.public_channel_service import PublicChannelService
from core.setting_types import BooleanSettingType
from core.tyrbot import Tyrbot
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
                    self.bot.send_private_channel_message("[Org]: %s" % message, fire_outgoing_event=False)
                else:
                    char_name = self.character_service.resolve_char_to_name(event_data.char_id)
                    self.bot.send_private_channel_message("[Org] %s: %s" % (char_name, message), fire_outgoing_event=False)

    @event(event_type=PrivateChannelService.PRIVATE_CHANNEL_MESSAGE_EVENT, description="Relay messages from the private channel to the org channel")
    def handle_private_channel_message_event(self, event_type, event_data):
        if event_data.char_id != self.bot.char_id:
            if event_data.message[0] != self.setting_service.get("symbol").get_value() or self.private_channel_relay_commands().get_value():
                char_name = self.character_service.resolve_char_to_name(event_data.char_id)
                self.bot.send_org_message("[Private] %s: %s" % (char_name, event_data.message), fire_outgoing_event=False)

    # TODO move to online_module
    @event(event_type=PrivateChannelService.JOINED_PRIVATE_CHANNEL_EVENT, description="Notify when a character joins the private channel")
    def handle_private_channel_joined_event(self, event_type, event_data):
        char_info = self.pork_service.get_character_info(event_data.char_id)
        if char_info:
            name = self.text.format_char_info(char_info)
        else:
            char_name = self.character_service.resolve_char_to_name(event_data.char_id)
            name = "<highlight>%s<end>" % char_name

        msg = "%s has joined the private channel." % name
        self.bot.send_org_message(msg, fire_outgoing_event=False)
        self.bot.send_private_channel_message(msg, fire_outgoing_event=False)

    # TODO move to online_module
    @event(event_type=PrivateChannelService.LEFT_PRIVATE_CHANNEL_EVENT, description="Notify when a character leaves the private channel")
    def handle_private_channel_left_event(self, event_type, event_data):
        char_name = self.character_service.resolve_char_to_name(event_data.char_id)
        msg = "<highlight>%s<end> has left the private channel." % char_name
        self.bot.send_org_message(msg, fire_outgoing_event=False)
        self.bot.send_private_channel_message(msg, fire_outgoing_event=False)

    # TODO move to online_module
    @event(event_type=OrgMemberController.ORG_MEMBER_LOGON_EVENT, description="Notify when org member logs on")
    def org_member_logon_event(self, event_type, event_data):
        if self.bot.is_ready():
            char_info = self.pork_service.get_character_info(event_data.char_id)
            if char_info:
                name = self.text.format_char_info(char_info)
            else:
                char_name = self.character_service.resolve_char_to_name(event_data.char_id)
                name = "<highlight>%s<end>" % char_name

            msg = "%s has logged on." % name
            self.bot.send_org_message(msg, fire_outgoing_event=False)
            self.bot.send_private_channel_message(msg, fire_outgoing_event=False)

    # TODO move to online_module
    @event(event_type=OrgMemberController.ORG_MEMBER_LOGOFF_EVENT, description="Notify when org member logs off")
    def org_member_logoff_event(self, event_type, event_data):
        if self.bot.is_ready():
            char_name = self.character_service.resolve_char_to_name(event_data.char_id)
            msg = "<highlight>%s<end> has logged off." % char_name
            self.bot.send_org_message(msg, fire_outgoing_event=False)
            self.bot.send_private_channel_message(msg, fire_outgoing_event=False)

    @event(event_type=Tyrbot.OUTGOING_PRIVATE_CHANNEL_MESSAGE_EVENT, description="Relay commands from the private channel to the org channel")
    def outgoing_private_channel_message_event(self, event_type, event_data):
        self.bot.send_org_message(event_data.message, fire_outgoing_event=False)

    @event(event_type=Tyrbot.OUTGOING_ORG_MESSAGE_EVENT, description="Relay commands from the org channel to the private channel")
    def outgoing_org_message_event(self, event_type, event_data):
        self.bot.send_private_channel_message(event_data.message, fire_outgoing_event=False)
