from core.decorators import instance, command, event, setting
from core.command_service import CommandService
from core.dict_object import DictObject
from core.logger import Logger
from core.setting_service import SettingService
from core.setting_types import BooleanSettingType


@instance()
class SystemController:
    SHUTDOWN_EVENT = "shutdown"

    shutdown_msg = "The bot is shutting down..."
    restart_msg = "The bot is restarting..."

    def __init__(self):
        self.logger = Logger(__name__)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.event_service = registry.get_instance("event_service")

    def pre_start(self):
        self.event_service.register_event_type(self.SHUTDOWN_EVENT)

    @setting(name="expected_shutdown", value="true", description="Helps bot to determine if last shutdown was expected or due to a problem")
    def expected_shutdown(self):
        return BooleanSettingType()

    @setting(name="restart_notify", value="true", description="Notify org and private channel when bot is restarting")
    def restart_notify(self):
        return BooleanSettingType()

    @command(command="shutdown", params=[], access_level="superadmin",
             description="Shutdown the bot")
    def shutdown_cmd(self, request):
        self.event_service.fire_event(self.SHUTDOWN_EVENT, DictObject({"restart": False}))

        # set expected flag
        self.expected_shutdown().set_value(True)

        if request.channel not in [CommandService.ORG_CHANNEL, CommandService.PRIVATE_CHANNEL]:
            request.reply(self.shutdown_msg)

        self.bot.shutdown()

    @command(command="restart", params=[], access_level="superadmin",
             description="Restart the bot")
    def restart_cmd(self, request):
        self.event_service.fire_event(self.SHUTDOWN_EVENT, DictObject({"restart": True}))

        # set expected flag
        self.expected_shutdown().set_value(True)

        if request.channel not in [CommandService.ORG_CHANNEL, CommandService.PRIVATE_CHANNEL]:
            request.reply(self.restart_msg)

        self.bot.restart()

    @event(event_type="connect", description="Notify superadmin that bot has come online")
    def connect_event(self, event_type, event_data):
        if self.expected_shutdown().get_value():
            msg = "<myname> is now <green>online<end>."
        else:
            self.logger.error("the bot has recovered from an unexpected shutdown or restart")
            msg = "<myname> is now <green>online<end> but may have shut down or restarted unexpectedly."

        self.bot.send_private_message(self.bot.superadmin, msg)
        self.bot.send_org_message(msg)
        self.bot.send_private_channel_message(msg)

        self.expected_shutdown().set_value(False)

    @event(event_type=SHUTDOWN_EVENT, description="Notify org channel on shutdown/restart")
    def notify_org_channel_shutdown_event(self, event_type, event_data):
        if event_data.restart:
            self.bot.send_org_message(self.restart_msg)
        else:
            self.bot.send_org_message(self.shutdown_msg)

    @event(event_type=SHUTDOWN_EVENT, description="Notify private channel on shutdown/restart")
    def notify_private_channel_shutdown_event(self, event_type, event_data):
        if event_data.restart:
            self.bot.send_private_channel_message(self.restart_msg)
        else:
            self.bot.send_private_channel_message(self.shutdown_msg)
