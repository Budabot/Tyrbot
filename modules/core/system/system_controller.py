import hjson

from core.command_param_types import Any
from core.decorators import instance, command, event, setting
from core.command_service import CommandService
from core.dict_object import DictObject
from core.logger import Logger
from core.setting_service import SettingService
from core.setting_types import BooleanSettingType
from core.translation_service import TranslationService


@instance()
class SystemController:
    SHUTDOWN_EVENT = "shutdown"

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.event_service = registry.get_instance("event_service")
        self.ts: TranslationService = registry.get_instance("translation_service")
        self.getresp = self.ts.get_response

    def pre_start(self):
        self.event_service.register_event_type(self.SHUTDOWN_EVENT)

    def start(self):
        self.ts.register_translation("module/system", self.load_system_channel_msg)

    def load_system_channel_msg(self):
        with open("modules/core/system/system.msg", mode="r", encoding="utf-8") as f:
            return hjson.load(f)

    @setting(name="expected_shutdown", value="true", description="Helps bot to determine if last shutdown was expected or due to a problem")
    def expected_shutdown(self):
        return BooleanSettingType()

    @setting(name="restart_notify", value="true", description="Notify org and private channel when bot is restarting")
    def restart_notify(self):
        return BooleanSettingType()

    @command(command="shutdown", params=[Any("reason", is_optional=True)], access_level="superadmin",
             description="Shutdown the bot")
    def shutdown_cmd(self, request, reason):
        if request.channel not in [CommandService.ORG_CHANNEL, CommandService.PRIVATE_CHANNEL]:
            request.reply(self._format_message(False, reason))
        self.shutdown(False, reason)

    @command(command="restart", params=[Any("reason", is_optional=True)], access_level="admin",
             description="Restart the bot")
    def restart_cmd(self, request, reason):
        if request.channel not in [CommandService.ORG_CHANNEL, CommandService.PRIVATE_CHANNEL]:
            request.reply(self._format_message(True, reason))
        self.shutdown(True, reason)

    @event(event_type="connect", description="Notify superadmin that bot has come online")
    def connect_event(self, event_type, event_data):
        if self.expected_shutdown().get_value():
            msg = self.getresp("module/system", "expected_online")
        else:
            self.logger.error("the bot has recovered from an unexpected shutdown or restart")
            msg = self.getresp("module/system", "unexpected_online")
        self.bot.send_private_message(self.bot.superadmin, msg)
        self.bot.send_org_message(msg, fire_outgoing_event=False)
        self.bot.send_private_channel_message(msg, fire_outgoing_event=False)

        self.expected_shutdown().set_value(False)

    @event(event_type=SHUTDOWN_EVENT, description="Notify org channel on shutdown/restart")
    def notify_org_channel_shutdown_event(self, event_type, event_data):
        self.bot.send_org_message(self._format_message(event_data.restart, event_data.reason), fire_outgoing_event=False)

    @event(event_type=SHUTDOWN_EVENT, description="Notify private channel on shutdown/restart")
    def notify_private_channel_shutdown_event(self, event_type, event_data):
        self.bot.send_private_channel_message(self._format_message(event_data.restart, event_data.reason), fire_outgoing_event=False)

    def shutdown(self, should_restart, reason=None):
        self.event_service.fire_event(self.SHUTDOWN_EVENT, DictObject({"restart": should_restart, "reason": reason}))
        # set expected flag
        self.expected_shutdown().set_value(True)
        if should_restart:
            self.bot.restart()
        else:
            self.bot.shutdown()

    def _format_message(self, restart, reason):
        if restart:
            if reason:
                return self.getresp("module/system", "restart") + self.getresp("module/system", "reason", {"reason": reason})
            return self.getresp("module/system", "restart") + ".."
        if reason:
            return self.getresp("module/system", "shutdown") + self.getresp("module/system", "reason", {"reason": reason})
        return self.getresp("module/system", "shutdown") + ".."


