from core.chat_blob import ChatBlob
from core.decorators import instance, event
from core.dict_object import DictObject
from core.logger import Logger
from core.public_channel_service import PublicChannelService
from core.text import Text
from core.tyrbot import Tyrbot
from modules.core.org_members.org_member_controller import OrgMemberController


@instance()
class OrgChannelController:
    RELAY_HUB_SOURCE = "org_channel"

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.character_service = registry.get_instance("character_service")
        self.relay_hub_service = registry.get_instance("relay_hub_service")
        self.ban_service = registry.get_instance("ban_service")
        self.log_controller = registry.get_instance("log_controller")
        self.online_controller = registry.get_instance("online_controller")
        self.relay_controller = registry.get_instance("relay_controller")
        self.text: Text = registry.get_instance("text")

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
            message = "[%s] %s" % (self.relay_controller.get_org_channel_prefix(), message)
        else:
            char_name = self.character_service.resolve_char_to_name(event_data.char_id)
            sender = DictObject({"char_id": event_data.char_id, "name": char_name})
            message = "[%s] %s: %s" % (self.relay_controller.get_org_channel_prefix(),
                                       self.text.make_charlink(char_name), message)

        self.relay_hub_service.send_message(self.RELAY_HUB_SOURCE, sender, message)

    @event(event_type=OrgMemberController.ORG_MEMBER_LOGON_EVENT, description="Notify when org member logs on")
    def org_member_logon_event(self, event_type, event_data):
        if self.bot.is_ready():
            msg = "%s has logged on. %s" % (self.online_controller.get_char_info_display(event_data.char_id),
                                            self.log_controller.get_logon(event_data.char_id))
            self.bot.send_org_message(msg)

    @event(event_type=OrgMemberController.ORG_MEMBER_LOGOFF_EVENT, description="Notify when org member logs off")
    def org_member_logoff_event(self, event_type, event_data):
        if self.bot.is_ready():
            char_name = self.character_service.resolve_char_to_name(event_data.char_id)
            msg = "<highlight>%s<end> has logged off. %s" % (char_name, self.log_controller.get_logoff(event_data.char_id))
            self.bot.send_org_message(msg)

    @event(event_type=Tyrbot.OUTGOING_ORG_MESSAGE_EVENT, description="Relay commands from the org channel to the relay hub")
    def outgoing_org_message_event(self, event_type, event_data):
        if isinstance(event_data.message, ChatBlob):
            message = event_data.message.title
        else:
            message = event_data.message

        message = "[%s] %s" % (self.relay_controller.get_org_channel_prefix(), message)

        self.relay_hub_service.send_message(self.RELAY_HUB_SOURCE, DictObject({"name": self.bot.char_name, "char_id": self.bot.char_id}), message)
