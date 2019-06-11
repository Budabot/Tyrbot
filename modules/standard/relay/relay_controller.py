from core.command_param_types import Any
from core.decorators import instance, command, event, setting
from core.private_channel_service import PrivateChannelService
from core.public_channel_service import PublicChannelService
from core.setting_types import TextSettingType
from modules.core.org_members.org_member_controller import OrgMemberController


@instance()
class RelayController:
    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.text = registry.get_instance("text")
        self.pork_service = registry.get_instance("pork_service")
        self.setting_service = registry.get_instance("setting_service")
        self.character_service = registry.get_instance("character_service")
        self.public_channel_service = registry.get_instance("public_channel_service")
        self.ban_service = registry.get_instance("ban_service")

    @setting(name="relay_bot", value="", description="Name of bot character for chat relay")
    def relay_bot(self):
        return TextSettingType()

    @setting(name="relay_prefix", value="", description="Name of this relay (if you don't want to use org or bot name)")
    def relay_prefix(self):
        return TextSettingType()

    @command(command="grc", params=[Any("message")], access_level="all",
             description="Accept incoming messages from relay bot")
    def grc_cmd(self, request, message):
        self.process_incoming_relay_message(request.sender, message)

    @event(event_type=PublicChannelService.ORG_CHANNEL_MESSAGE_EVENT, description="Relay messages from the org channel to the relay")
    def handle_org_message_event(self, event_type, event_data):
        if event_data.char_id != self.bot.char_id and event_data.message[0] != self.setting_service.get("symbol").get_value():
            if event_data.char_id == 4294967295:
                self.send_message_to_relay(event_data.message)
            elif not self.ban_service.get_ban(event_data.char_id):
                char_name = self.character_service.resolve_char_to_name(event_data.char_id)
                self.send_message_to_relay("%s: %s" % (char_name, event_data.message))

    @event(event_type=PrivateChannelService.PRIVATE_CHANNEL_MESSAGE_EVENT, description="Relay messages from the private channel to the relay")
    def handle_private_channel_message_event(self, event_type, event_data):
        if event_data.char_id != self.bot.char_id and event_data.message[0] != self.setting_service.get("symbol").get_value():
            if not self.ban_service.get_ban(event_data.char_id):
                char_name = self.character_service.resolve_char_to_name(event_data.char_id)
                self.send_message_to_relay("[Private] %s: %s" % (char_name, event_data.message))

    @event(event_type=PrivateChannelService.JOINED_PRIVATE_CHANNEL_EVENT, description="Notify relay when a character joins the private channel")
    def handle_private_channel_joined_event(self, event_type, event_data):
        char_info = self.pork_service.get_character_info(event_data.char_id)
        if char_info:
            name = self.text.format_char_info(char_info)
        else:
            char_name = self.character_service.resolve_char_to_name(event_data.char_id)
            name = "<highlight>%s<end>" % char_name

        self.send_message_to_relay("%s has joined the private channel." % name)

    @event(event_type=PrivateChannelService.LEFT_PRIVATE_CHANNEL_EVENT, description="Notify relay when a character leaves the private channel")
    def handle_private_channel_left_event(self, event_type, event_data):
        char_name = self.character_service.resolve_char_to_name(event_data.char_id)
        msg = "<highlight>%s<end> has left the private channel." % char_name
        self.send_message_to_relay(msg)

    @event(event_type=OrgMemberController.ORG_MEMBER_LOGON_EVENT, description="Notify relay when org member logs on")
    def org_member_logon_event(self, event_type, event_data):
        if self.bot.is_ready():
            char_info = self.pork_service.get_character_info(event_data.char_id)
            if char_info:
                name = self.text.format_char_info(char_info)
            else:
                char_name = self.character_service.resolve_char_to_name(event_data.char_id)
                name = "<highlight>%s<end>" % char_name

            msg = "%s has logged on." % name
            self.send_message_to_relay(msg)

    @event(event_type=OrgMemberController.ORG_MEMBER_LOGOFF_EVENT, description="Notify relay when org member logs off")
    def org_member_logoff_event(self, event_type, event_data):
        if self.bot.is_ready():
            char_name = self.character_service.resolve_char_to_name(event_data.char_id)
            msg = "<highlight>%s<end> has logged off." % char_name
            self.send_message_to_relay(msg)

    def process_incoming_relay_message(self, sender, message):
        relay_bot = self.relay_bot().get_value()
        if relay_bot and sender.name.lower() == relay_bot.lower():
            self.bot.send_org_message(message, fire_outgoing_event=False)
            self.bot.send_private_channel_message(message, fire_outgoing_event=False)

    def send_message_to_relay(self, message):
        relay_bot = self.relay_bot().get_value()
        if relay_bot:
            # if setting, then use setting, else if org, then use org name, else use botname
            prefix = self.relay_prefix().get_value() or self.public_channel_service.get_org_name() or "<myname>"

            self.bot.send_private_message(relay_bot, "grc [%s] %s" % (prefix, message), add_color=False)
