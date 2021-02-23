from core.decorators import instance, event
from core.setting_types import TextSettingType
from modules.standard.discord.discord_message import DiscordTextMessage


@instance()
class DiscordExtraRelayController:
    MESSAGE_SOURCE = "discord_extra_relay"

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.setting_service = registry.get_instance("setting_service")
        self.message_hub_service = registry.get_instance("message_hub_service")
        self.discord_controller = registry.get_instance("discord_controller")

    def start(self):
        self.setting_service.register(self.module_name, "discord_extra_relay_channel_id", "", TextSettingType(allow_empty=True),
                                      "Discord channel id for relaying extra messages to")

        self.message_hub_service.register_message_destination(self.MESSAGE_SOURCE,
                                                              self.handle_incoming_relay_message,
                                                              [],
                                                              [])

    def handle_incoming_relay_message(self, ctx):
        channel = self.get_discord_channel(self.setting_service.get("discord_extra_relay_channel_id").get_value())
        if channel:
            discord_message = DiscordTextMessage(self.discord_controller.strip_html_tags(ctx.formatted_message), channel)
            self.discord_controller.send_to_discord("msg", discord_message)

    def get_discord_channel(self, channel_id):
        if not self.discord_controller.is_connected():
            return None

        for channel in self.discord_controller.client.get_text_channels():
            if str(channel.id) == channel_id:
                return channel
        return None
