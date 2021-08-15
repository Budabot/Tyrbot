from core.command_param_types import Any
from core.decorators import instance, command, event
from core.dict_object import DictObject
from core.logger import Logger
from core.private_channel_service import PrivateChannelService
from core.public_channel_service import PublicChannelService
from core.setting_service import SettingService
from core.setting_types import BooleanSettingType


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
        self.character_service = registry.get_instance("character_service")
        self.message_hub_service = registry.get_instance("message_hub_service")

    def pre_start(self):
        self.event_service.register_event_type(self.SHUTDOWN_EVENT)
        self.message_hub_service.register_message_source(self.MESSAGE_SOURCE)

    def start(self):
        self.setting_service.register(self.module_name, "expected_shutdown", True, BooleanSettingType(),
                                      "Helps bot to determine if last shutdown was expected or due to a problem")

    def expected_shutdown(self):
        return self.setting_service.get("expected_shutdown")

    @command(command="shutdown", params=[Any("reason", is_optional=True)], access_level="superadmin",
             description="Shutdown the bot")
    def shutdown_cmd(self, request, reason):
        if request.channel not in [PublicChannelService.ORG_CHANNEL_COMMAND, PrivateChannelService.PRIVATE_CHANNEL_COMMAND]:
            request.reply(self._format_message(False, reason))
        self.shutdown(False, reason)

    @command(command="restart", params=[Any("reason", is_optional=True)], access_level="admin",
             description="Restart the bot")
    def restart_cmd(self, request, reason):
        if request.channel not in [PublicChannelService.ORG_CHANNEL_COMMAND, PrivateChannelService.PRIVATE_CHANNEL_COMMAND]:
            request.reply(self._format_message(True, reason))
        self.shutdown(True, reason)

    @event(event_type="connect", description="Notify superadmin that bot has come online")
    def connect_event(self, event_type, event_data):
        if self.expected_shutdown().get_value():
            msg = "<myname> is now <green>online</green>."
        else:
            self.logger.warning("The bot has recovered from an unexpected shutdown or restart")
            msg = "<myname> is now <green>online</green> but may have shut down or restarted unexpectedly."

        char_id = self.character_service.resolve_char_to_id(self.bot.superadmin)
        self.bot.send_private_message(char_id, msg, conn=self.bot.get_primary_conn())
        self.bot.send_private_channel_message(msg, conn=self.bot.get_primary_conn())
        for _id, conn in self.bot.get_conns(lambda x: x.is_main):
            self.bot.send_org_message(msg, conn=conn)

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
        msg = ""
        if restart:
            msg += "The bot is restarting."
        else:
            msg += "The bot is shutting down."

        if reason:
            msg += f" <highlight>Reason: {reason}</highlight>"

        return msg
