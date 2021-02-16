import hjson

from core.ban_service import BanService
from core.chat_blob import ChatBlob
from core.command_param_types import Character
from core.command_service import CommandService
from core.decorators import instance, command, event
from core.dict_object import DictObject
from core.private_channel_service import PrivateChannelService
from core.setting_service import SettingService
from core.text import Text
from core.translation_service import TranslationService


@instance()
class PrivateChannelController:
    MESSAGE_SOURCE = "private_channel"
    PRIVATE_CHANNEL_PREFIX = "[Priv]"

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.private_channel_service = registry.get_instance("private_channel_service")
        self.character_service = registry.get_instance("character_service")
        self.job_scheduler = registry.get_instance("job_scheduler")
        self.access_service = registry.get_instance("access_service")
        self.message_hub_service = registry.get_instance("message_hub_service")
        self.ban_service = registry.get_instance("ban_service")
        self.log_controller = registry.get_instance("log_controller", is_optional=True)  # TODO core module depending on standard module
        self.online_controller = registry.get_instance("online_controller", is_optional=True)  # TODO core module depending on standard module
        self.text: Text = registry.get_instance("text")
        self.ts: TranslationService = registry.get_instance("translation_service")
        self.getresp = self.ts.get_response
        self.setting_service: SettingService = registry.get_instance("setting_service")

    def pre_start(self):
        self.message_hub_service.register_message_source(self.MESSAGE_SOURCE)

    def start(self):
        self.message_hub_service.register_message_destination(self.MESSAGE_SOURCE,
                                                              self.handle_incoming_relay_message,
                                                              ["org_channel", "discord", "websocket_relay", "tell_relay", "broadcast", "raffle", "shutdown_notice", "raid"],
                                                              [self.MESSAGE_SOURCE])
        self.ts.register_translation("module/private_channel", self.load_private_channel_msg)

    def load_private_channel_msg(self):
        with open("modules/core/private_channel/private_channel.msg", mode="r", encoding="utf-8") as f:
            return hjson.load(f)

    def handle_incoming_relay_message(self, ctx):
        self.bot.send_private_channel_message(ctx.formatted_message, conn=self.get_conn())

    @command(command="join", params=[], access_level="member",
             description="Join the private channel")
    def join_cmd(self, request):
        self.private_channel_service.invite(request.sender.char_id, self.get_conn())

    @command(command="leave", params=[], access_level="all",
             description="Leave the private channel")
    def leave_cmd(self, request):
        self.private_channel_service.kick(request.sender.char_id, self.get_conn())

    @command(command="invite", params=[Character("character")], access_level="all",
             description="Invite a character to the private channel")
    def invite_cmd(self, request, char):
        if char.char_id:
            if char.char_id in request.conn.private_channel:
                return self.getresp("module/private_channel", "invite_fail", {"target": char.name})
            else:
                conn = self.get_conn()
                self.bot.send_private_message(char.char_id,
                                              self.getresp("module/private_channel", "invite_success_target", {"inviter": request.sender.name}),
                                              conn=conn)
                self.private_channel_service.invite(char.char_id, conn)
                return self.getresp("module/private_channel", "invite_success_self", {"target": char.name})
        else:
            return self.getresp("global", "char_not_found", {"char": char.name})

    @command(command="kick", params=[Character("character")], access_level="moderator",
             description="Kick a character from the private channel")
    def kick_cmd(self, request, char):
        if char.char_id:
            if char.char_id not in request.conn.private_channel:
                return self.getresp("module/private_channel", "kick_fail_not_in_priv", {"target": char.name})
            else:
                # TODO use request.sender.access_level and char.access_level
                if self.access_service.has_sufficient_access_level(request.sender.char_id, char.char_id):
                    conn = self.get_conn()
                    self.bot.send_private_message(char.char_id,
                                                  self.getresp("module/private_channel", "kick_success_target", {"kicker": request.sender.name}),
                                                  conn=conn)
                    self.private_channel_service.kick(char.char_id, conn)
                    return self.getresp("module/private_channel", "kick_success_self", {"target": char.name})
                else:
                    return self.getresp("module/private_channel", "kick_fail", {"target": char.name})
        else:
            return self.getresp("global", "char_not_found", {"char": char.name})

    @command(command="kickall", params=[], access_level="moderator",
             description="Kick all characters from the private channel")
    def kickall_cmd(self, request):
        conn = self.get_conn()
        self.bot.send_private_channel_message(self.getresp("module/private_channel", "kick_all", {"char": request.sender.name}), conn=conn)
        self.job_scheduler.delayed_job(lambda t: self.private_channel_service.kickall(conn), 10)

    @event(event_type=BanService.BAN_ADDED_EVENT, description="Kick characters from the private channel who are banned", is_hidden=True)
    def ban_added_event(self, event_type, event_data):
        self.private_channel_service.kick_from_all(event_data.char_id)

    @event(event_type=PrivateChannelService.PRIVATE_CHANNEL_MESSAGE_EVENT, description="Relay messages from the private channel to the relay hub", is_hidden=True)
    def handle_private_channel_message_event(self, event_type, event_data):
        if self.bot.get_conn_by_char_id(event_data.char_id) or self.ban_service.get_ban(event_data.char_id):
            return

        char_name = event_data.name
        sender = DictObject({"char_id": event_data.char_id, "name": char_name})
        char = self.text.make_charlink(char_name)
        formatted_message = "{priv} {char}: {message}".format(priv=self.PRIVATE_CHANNEL_PREFIX, char=char, message=event_data.message)
        self.message_hub_service.send_message(self.MESSAGE_SOURCE, sender, event_data.message, formatted_message)

    @event(event_type=PrivateChannelService.JOINED_PRIVATE_CHANNEL_EVENT, description="Notify when a character joins the private channel")
    def handle_private_channel_joined_event(self, event_type, event_data):
        if self.online_controller:
            char_info = self.online_controller.get_char_info_display(event_data.char_id, self.get_conn())
        else:
            char_info = self.character_service.resolve_char_to_name(event_data.char_id)
        msg = self.getresp("module/private_channel", "join",
                           {"char": char_info,
                            "logon": self.log_controller.get_logon(event_data.char_id) if self.log_controller else ""})

        self.bot.send_private_channel_message(msg, conn=self.get_conn())
        self.message_hub_service.send_message(self.MESSAGE_SOURCE, None, None, msg)

    @event(event_type=PrivateChannelService.LEFT_PRIVATE_CHANNEL_EVENT, description="Notify when a character leaves the private channel")
    def handle_private_channel_left_event(self, event_type, event_data):
        msg = self.getresp("module/private_channel", "leave",
                           {"char": event_data.name,
                            "logoff": self.log_controller.get_logoff(event_data.char_id) if self.log_controller else ""})

        self.bot.send_private_channel_message(msg, conn=self.get_conn())
        self.message_hub_service.send_message(self.MESSAGE_SOURCE, None, None, msg)

    @event(event_type=CommandService.PRIVATE_CHANNEL_COMMAND_EVENT, description="Relay commands from the private channel to the relay hub", is_hidden=True)
    def outgoing_private_channel_message_event(self, event_type, event_data):
        if isinstance(event_data.message, ChatBlob):
            pages = self.text.paginate(ChatBlob(event_data.message.title, event_data.message.msg),
                                       event_data.conn,
                                       self.setting_service.get("org_channel_max_page_length").get_value())
            if len(pages) < 4:
                for page in pages:
                    message = "{priv} {message}".format(priv=self.PRIVATE_CHANNEL_PREFIX, message=page)
                    self.message_hub_service.send_message(self.MESSAGE_SOURCE,
                                                          None,
                                                          page,
                                                          message)
            else:
                message = "{priv} {message}".format(priv=self.PRIVATE_CHANNEL_PREFIX, message=event_data.message.title)
                self.message_hub_service.send_message(self.MESSAGE_SOURCE,
                                                      None,
                                                      event_data.message.title,
                                                      message)
        else:
            message = "{priv} {message}".format(priv=self.PRIVATE_CHANNEL_PREFIX, message=event_data.message)
            self.message_hub_service.send_message(self.MESSAGE_SOURCE,
                                                  None,
                                                  event_data.message,
                                                  message)

    def get_conn(self):
        # always invite to primary conn priv channel
        return self.bot.get_primary_conn()
