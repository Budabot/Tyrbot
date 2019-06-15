import json
import threading

from core.decorators import instance, event, timerevent, setting
from core.logger import Logger
from core.lookup.character_service import CharacterService
from core.private_channel_service import PrivateChannelService
from core.public_channel_service import PublicChannelService
from core.setting_types import ColorSettingType, TextSettingType
from core.text import Text
from .websocket_relay_worker import WebsocketRelayWorker


@instance()
class WebsocketRelayController:
    def __init__(self):
        self.dthread = None
        self.queue = []
        self.logger = Logger(__name__)
        self.worker = None

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.setting_service = registry.get_instance("setting_service")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.text: Text = registry.get_instance("text")

    @setting(name="websocket_relay_server_address", value="ws://localhost/subscribe/relay", description="The address of the websocket relay server")
    def websocket_relay_server_address(self):
        return TextSettingType(["ws://localhost/subscribe/relay"])

    @setting(name="websocket_relay_channel_color", value="#FFFF00", description="Color of the channel in Websocket relay messages")
    def websocket_channel_color(self):
        return ColorSettingType()

    @setting(name="websocket_relay_message_color", value="#FCA712", description="Color of the message content in Websocket relay messages")
    def websocket_message_color(self):
        return ColorSettingType()

    @setting(name="websocket_relay_sender_color", value="#00DE42", description="Color of the sender in Websocket relay messages")
    def websocket_sender_color(self):
        return ColorSettingType()

    @timerevent(budatime="1s", description="Relay messages from Websocket relay to org and private channel")
    def handle_queue_event(self, event_type, event_data):
        while self.queue:
            obj = self.queue.pop(0)
            if obj.type == "message":
                payload = obj.payload
                message = ("[Relay] <channel_color>[%s]<end> <sender_color>%s<end>: <message_color>%s<end>" % (payload.channel, payload.sender.name, payload.message))\
                    .replace("<channel_color>", self.websocket_channel_color().get_font_color())\
                    .replace("<message_color>", self.websocket_message_color().get_font_color())\
                    .replace("<sender_color>", self.websocket_sender_color().get_font_color())

                self.bot.send_org_message(message, fire_outgoing_event=False)
                self.bot.send_private_channel_message(message, fire_outgoing_event=False)

    @event(event_type="connect", description="Connect to Websocket relay on startup")
    def handle_connect_event(self, event_type, event_data):
        self.connect()

    @event(event_type=PrivateChannelService.PRIVATE_CHANNEL_MESSAGE_EVENT, description="Relay messages from the private channel to Websocket relay")
    def handle_private_channel_message_event(self, event_type, event_data):
        self.process_message(event_data, "Private")

    @event(event_type=PublicChannelService.ORG_CHANNEL_MESSAGE_EVENT, description="Relay messages from the org channel to Websocket relay")
    def handle_org_channel_message_event(self, event_type, event_data):
        self.process_message(event_data, "Org")

    def process_message(self, event_data, channel):
        if event_data.char_id != self.bot.char_id and event_data.message[0] != self.setting_service.get("symbol").get_value():
            char_name = self.character_service.resolve_char_to_name(event_data.char_id)
            obj = json.dumps({"sender": {"char_id": event_data.char_id, "name": char_name},
                              "message": event_data.message,
                              "channel": channel})
            self.worker.send_message(obj)

    def connect(self):
        self.worker = WebsocketRelayWorker(self.queue, self.websocket_relay_server_address().get_value())

        self.disconnect()
        self.dthread = threading.Thread(target=self.worker.run, daemon=True)
        self.dthread.start()

    def disconnect(self):
        # TODO
        pass
