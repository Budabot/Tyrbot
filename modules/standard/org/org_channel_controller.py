from core.chat_blob import ChatBlob
from core.decorators import instance, event, setting
from core.dict_object import DictObject
from core.logger import Logger
from core.public_channel_service import PublicChannelService
from core.setting_service import SettingService
from core.setting_types import BooleanSettingType
from core.text import Text
from core.tyrbot import Tyrbot
from modules.core.org_members.org_member_controller import OrgMemberController


@instance()
class OrgChannelController:
    MESSAGE_SOURCE = "org_channel"
    ORG_CHANNEL_PREFIX = "[Org]"

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.character_service = registry.get_instance("character_service")
        self.message_hub_service = registry.get_instance("message_hub_service")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.ban_service = registry.get_instance("ban_service")
        self.log_controller = registry.get_instance("log_controller", is_optional=True)
        self.online_controller = registry.get_instance("online_controller")
        self.text: Text = registry.get_instance("text")

    def pre_start(self):
        self.message_hub_service.register_message_source(self.MESSAGE_SOURCE)

    def start(self):
        self.message_hub_service.register_message_destination(
            self.MESSAGE_SOURCE, self.handle_incoming_relay_message,
            ["private_channel", "discord", "websocket_relay", "tell_relay", "broadcast", "raffle", "cloak_reminder", "wave_counter"],
            [self.MESSAGE_SOURCE])

    def handle_incoming_relay_message(self, ctx):
        self.bot.send_org_message(ctx.formatted_message, fire_outgoing_event=False)

    @setting(name="prefix_org_priv", value="true", description="Should the prefix [org] be displayed in relayed messages", )
    def prefix_priv(self):
        return BooleanSettingType()

    @event(event_type=PublicChannelService.ORG_CHANNEL_MESSAGE_EVENT, description="Relay messages from the org channel to the relay hub", is_hidden=True)
    def handle_org_message_event(self, event_type, event_data):
        if event_data.char_id == self.bot.char_id or self.ban_service.get_ban(event_data.char_id):
            return

        if event_data.extended_message:
            message = event_data.extended_message.get_message()
        else:
            message = event_data.message

        if event_data.char_id == 4294967295 or event_data.char_id == 0:
            sender = None
            formatted_message = "{org} {msg}".format(org=self.ORG_CHANNEL_PREFIX,
                                                     msg=message)
        else:
            char_name = self.character_service.resolve_char_to_name(event_data.char_id)
            sender = DictObject({"char_id": event_data.char_id, "name": char_name})
            formatted_message = "{org} {char}: {msg}".format(org=self.ORG_CHANNEL_PREFIX,
                                                             char=self.text.make_charlink(char_name),
                                                             msg=message)

        self.message_hub_service.send_message(self.MESSAGE_SOURCE, sender, message, formatted_message)

    @event(event_type=OrgMemberController.ORG_MEMBER_LOGON_EVENT, description="Notify when org member logs on")
    def org_member_logon_event(self, event_type, event_data):
        if self.bot.is_ready():
            msg = "%s has logged on. %s" % (self.online_controller.get_char_info_display(event_data.char_id),
                                            self.log_controller.get_logon(event_data.char_id) if self.log_controller else "")
            self.bot.send_org_message(msg)

    @event(event_type=OrgMemberController.ORG_MEMBER_LOGOFF_EVENT, description="Notify when org member logs off")
    def org_member_logoff_event(self, event_type, event_data):
        if self.bot.is_ready():
            char_name = self.character_service.resolve_char_to_name(event_data.char_id)
            msg = "<highlight>%s<end> has logged off. %s" % (char_name,
                                                             self.log_controller.get_logoff(event_data.char_id) if self.log_controller else "")
            self.bot.send_org_message(msg)

    @event(event_type=Tyrbot.OUTGOING_ORG_MESSAGE_EVENT, description="Relay commands from the org channel to the relay hub")
    def outgoing_org_message_event(self, event_type, event_data):
        if isinstance(event_data.message, ChatBlob):
            pages = self.text.paginate(ChatBlob(event_data.message.title, event_data.message.msg), self.setting_service.get("org_channel_max_page_length").get_value())
            if len(pages) < 4:
                for page in pages:
                    message = "{org} {message}".format(org=self.ORG_CHANNEL_PREFIX, message=page)
                    self.message_hub_service.send_message(self.MESSAGE_SOURCE,
                                                          None,
                                                          page,
                                                          message)
            else:
                message ="{org} {message}".format(org=self.ORG_CHANNEL_PREFIX, message=event_data.message.title)
                self.message_hub_service.send_message(self.MESSAGE_SOURCE,
                                                      None,
                                                      event_data.message.title,
                                                      message)
        else:
            message = "{org} {message}".format(org=self.ORG_CHANNEL_PREFIX, message=event_data.message)
            self.message_hub_service.send_message(self.MESSAGE_SOURCE,
                                                  None,
                                                  event_data.message,
                                                  message)
