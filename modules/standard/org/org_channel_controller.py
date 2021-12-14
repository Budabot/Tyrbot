from core.chat_blob import ChatBlob
from core.command_param_types import Const, Int, Any
from core.decorators import instance, event, command
from core.dict_object import DictObject
from core.logger import Logger
from core.public_channel_service import PublicChannelService
from core.setting_service import SettingService
from core.setting_types import DictionarySettingType
from core.text import Text
from modules.core.org_members.org_member_controller import OrgMemberController


@instance()
class OrgChannelController:
    MESSAGE_SOURCE = "org_channel"

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.character_service = registry.get_instance("character_service")
        self.message_hub_service = registry.get_instance("message_hub_service")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.ban_service = registry.get_instance("ban_service")
        self.log_controller = registry.get_instance("log_controller", is_optional=True)
        self.online_controller = registry.get_instance("online_controller", is_optional=True)
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.text: Text = registry.get_instance("text")

    def pre_start(self):
        self.message_hub_service.register_message_source(self.MESSAGE_SOURCE)

    def start(self):
        self.setting_service.register(self.module_name, "org_abbreviations", "", DictionarySettingType(), "Org Abbreviates for relay messages")

        self.message_hub_service.register_message_destination(
            self.MESSAGE_SOURCE, self.handle_incoming_relay_message,
            ["private_channel", "discord", "websocket_relay", "broadcast", "raffle", "cloak_reminder", "wave_counter", "shutdown_notice", "raid", "tower_attacks", "timers"],
            [self.MESSAGE_SOURCE])

        self.command_alias_service.add_alias("orgabbreviations", "orgabbreviation")

    def handle_incoming_relay_message(self, ctx):
        for _id, conn in self.bot.get_conns(lambda x: x.is_main and x.org_id):
            self.bot.send_org_message(ctx.formatted_message, conn=conn)

    @command(command="orgabbreviation", params=[], access_level="admin",
             description="List the current org abbreviations for relay messages")
    def orgabbreviation_list_command(self, request):
        org_abbreviations = self.setting_service.get("org_abbreviations").get_value()

        blob = ""
        for k, v in org_abbreviations.items():
            blob += f"{k} = '<highlight>{v}</highlight>'\n"

        return ChatBlob("Org Abbreviations (%d)" % len(org_abbreviations), blob)

    @command(command="orgabbreviation", params=[Const("set"), Int("org_id"), Any("abbreviation")], access_level="admin",
             description="Set an org abbreviation for relay messages")
    def orgabbreviation_set_command(self, request, _, org_id, abbreviation):
        self.set_org_abbreviation(org_id, abbreviation)
        return f"Org abbreviation <highlight>{abbreviation}</highlight> has been set for org id <highlight>{org_id}</highlight>."

    @command(command="orgabbreviation", params=[Const("clear"), Int("org_id")], access_level="admin",
             description="Clear an org abbreviation for relay messages")
    def orgabbreviation_clear_command(self, request, _, org_id):
        if not self.set_org_abbreviation(org_id, None):
            return f"Org abbreviation for org id <highlight>{org_id}</highlight> has not been set."
        else:
            return f"Org abbreviation has been cleared for org id <highlight>{org_id}</highlight>."

    def set_org_abbreviation(self, org_id, abbreviation):
        org_id = str(org_id)
        org_abbreviations = self.setting_service.get("org_abbreviations").get_value()

        if abbreviation:
            org_abbreviations[org_id] = abbreviation
        else:
            if org_id in org_abbreviations:
                del org_abbreviations[org_id]
            else:
                return False

        self.setting_service.get("org_abbreviations").set_value(org_abbreviations)
        return True

    @event(event_type=PublicChannelService.ORG_CHANNEL_MESSAGE_EVENT, description="Relay messages from the org channel to the relay hub", is_system=True)
    def handle_org_message_event(self, event_type, event_data):
        if self.bot.get_conn_by_char_id(event_data.char_id) or self.ban_service.get_ban(event_data.char_id):
            return

        org_abbreviation = self.get_org_abbreviation(event_data.conn)

        if event_data.extended_message:
            message = event_data.extended_message.get_message()
        else:
            message = event_data.message

        if event_data.char_id == 4294967295 or event_data.char_id == 0:
            sender = None
            formatted_message = "{org} {msg}".format(org=org_abbreviation,
                                                     msg=message)
        else:
            sender = DictObject({"char_id": event_data.char_id, "name": event_data.name})
            formatted_message = "{org} {char}: {msg}".format(org=org_abbreviation,
                                                             char=self.text.make_charlink(event_data.name),
                                                             msg=message)

        self.bot.send_message_to_other_org_channels(formatted_message, from_conn=event_data.conn)
        self.message_hub_service.send_message(self.MESSAGE_SOURCE, sender, org_abbreviation, message)

    @event(event_type=OrgMemberController.ORG_MEMBER_LOGON_EVENT, description="Notify when org member logs on")
    def org_member_logon_event(self, event_type, event_data):
        if self.bot.is_ready():
            if self.online_controller:
                char_info = self.online_controller.get_char_info_display(event_data.char_id, event_data.conn)
            else:
                char_info = self.character_service.resolve_char_to_name(event_data.char_id, f"Unknown({event_data.char_id})")

            msg = f"{char_info} has logged on."
            if self.log_controller:
                msg += " " + self.log_controller.get_logon(event_data.char_id)

            for _id, conn in self.bot.get_conns(lambda x: x.is_main and x.org_id):
                if event_data.conn == conn:
                    self.bot.send_org_message(msg, conn=conn)
                else:
                    self.bot.send_org_message(self.get_org_abbreviation(event_data.conn) + " " + msg, conn=conn)
            self.message_hub_service.send_message(self.MESSAGE_SOURCE, None, self.get_org_abbreviation(event_data.conn), msg)

    @event(event_type=OrgMemberController.ORG_MEMBER_LOGOFF_EVENT, description="Notify when org member logs off")
    def org_member_logoff_event(self, event_type, event_data):
        if self.bot.is_ready():
            char_name = event_data.name or f"Unknown({event_data.char_id})"
            msg = f"<highlight>{char_name}</highlight> has logged off."
            if self.log_controller:
                msg += " " + self.log_controller.get_logoff(event_data.char_id)

            for _id, conn in self.bot.get_conns(lambda x: x.is_main and x.org_id):
                if event_data.conn == conn:
                    self.bot.send_org_message(msg, conn=conn)
                else:
                    self.bot.send_org_message(self.get_org_abbreviation(event_data.conn) + " " + msg, conn=conn)
            self.message_hub_service.send_message(self.MESSAGE_SOURCE, None, self.get_org_abbreviation(event_data.conn), msg)

    @event(event_type=PublicChannelService.ORG_CHANNEL_COMMAND_EVENT, description="Relay commands from the org channel to the relay hub", is_system=True)
    def outgoing_org_message_event(self, event_type, event_data):
        org_abbreviation = self.get_org_abbreviation(event_data.conn)
        msg = org_abbreviation + " "
        sender = None
        if event_data.name:
            msg += self.text.make_charlink(event_data.name) + ": "
            sender = DictObject({"char_id": event_data.char_id, "name": event_data.name})

        if isinstance(event_data.message, ChatBlob):
            pages = self.text.paginate(ChatBlob(event_data.message.title, event_data.message.msg),
                                       event_data.conn,
                                       self.setting_service.get("org_channel_max_page_length").get_value())
            if len(pages) < 4:
                for page in pages:
                    message = msg + page
                    self.bot.send_message_to_other_org_channels(message, from_conn=event_data.conn)
                    self.message_hub_service.send_message(self.MESSAGE_SOURCE, sender, org_abbreviation, page)
            else:
                message = msg + event_data.message.title
                self.bot.send_message_to_other_org_channels(message, from_conn=event_data.conn)
                self.message_hub_service.send_message(self.MESSAGE_SOURCE, sender, org_abbreviation, event_data.message.title)
        else:
            message = msg + event_data.message
            self.bot.send_message_to_other_org_channels(message, from_conn=event_data.conn)
            self.message_hub_service.send_message(self.MESSAGE_SOURCE, sender, org_abbreviation, event_data.message)

    def get_org_abbreviation(self, conn):
        org_abbreviations = self.setting_service.get("org_abbreviations").get_value()
        return "[%s]" % org_abbreviations.get(str(conn.org_id), conn.get_org_name())
