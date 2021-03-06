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
    MESSAGE_SOURCE = "shutdown_notice"

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.event_service = registry.get_instance("event_service")
        self.ts: TranslationService = registry.get_instance("translation_service")
        self.message_hub_service = registry.get_instance("message_hub_service")
        self.getresp = self.ts.get_response

    def pre_start(self):
        self.event_service.register_event_type(self.SHUTDOWN_EVENT)
        self.message_hub_service.register_message_source(self.MESSAGE_SOURCE)

    def start(self):
        self.ts.register_translation("module/system", self.load_system_msg)

        self.setting_service.register_new(self.module_name, "expected_shutdown", True, BooleanSettingType(),
                                          "Helps bot to determine if last shutdown was expected or due to a problem")

    def load_system_msg(self):
        with open("modules/core/system/system.msg", mode="r", encoding="utf-8") as f:
            return hjson.load(f)

    def expected_shutdown(self):
        return self.setting_service.get("expected_shutdown")

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

    def shutdown(self, should_restart, reason=None):
        self.event_service.fire_event(self.SHUTDOWN_EVENT, DictObject({"restart": should_restart, "reason": reason}))
        # set expected flag
        self.expected_shutdown().set_value(True)
        self.message_hub_service.send_message(self.MESSAGE_SOURCE, None, None, self._format_message(should_restart, reason))
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
