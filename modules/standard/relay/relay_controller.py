from core.command_param_types import Any
from core.decorators import instance, command, setting
from core.setting_types import TextSettingType


@instance()
class RelayController:
    RELAY_HUB_SOURCE = "tell_relay"

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.text = registry.get_instance("text")
        self.pork_service = registry.get_instance("pork_service")
        self.setting_service = registry.get_instance("setting_service")
        self.character_service = registry.get_instance("character_service")
        self.public_channel_service = registry.get_instance("public_channel_service")
        self.relay_hub_service = registry.get_instance("relay_hub_service")
        self.ban_service = registry.get_instance("ban_service")

    def start(self):
        self.relay_hub_service.register_relay(self.RELAY_HUB_SOURCE, self.handle_incoming_relay_message)

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

    def process_incoming_relay_message(self, sender, message):
        relay_bot = self.relay_bot().get_value()
        if relay_bot and sender.name.lower() == relay_bot.lower():
            self.relay_hub_service.send_message(self.RELAY_HUB_SOURCE, None, message)

    def handle_incoming_relay_message(self, ctx):
        message = ctx.message

        self.send_message_to_relay(message)

    def send_message_to_relay(self, message):
        relay_bot = self.relay_bot().get_value()
        if relay_bot:
            # if setting, then use setting, else if org, then use org name, else use botname
            prefix = self.get_org_channel_prefix()

            self.bot.send_private_message(relay_bot, "grc [%s] %s" % (prefix, message), add_color=False)

    def get_org_channel_prefix(self):
        return self.relay_prefix().get_value() or self.public_channel_service.get_org_name() or self.bot.char_name
