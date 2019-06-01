import json
import threading

from core.decorators import instance, event, timerevent, setting
from core.logger import Logger
from core.lookup.character_service import CharacterService
from core.private_channel_service import PrivateChannelService
from core.setting_types import ColorSettingType
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
        self.db = registry.get_instance("db")
        self.setting_service = registry.get_instance("setting_service")
        self.event_service = registry.get_instance("event_service")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.text: Text = registry.get_instance("text")

    def start(self):
        self.worker = WebsocketRelayWorker(self.queue, "wss://gridnet.jkbff.com/subscribe/gridnet.rk%d" % 6)

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
            message = "[Relay] %s" % obj.payload.message\
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
        if event_data.char_id != self.bot.char_id and event_data.message[0] != self.setting_service.get("symbol").get_value():
            char_name = self.character_service.resolve_char_to_name(event_data.char_id)
            obj = json.dumps({"sender": {"char_id": event_data.char_id, "name": char_name},
                              "message": "[Private] %s: %s" % (char_name, event_data.message),
                              "channel": "Private"})
            self.worker.send_message(obj)

    def connect(self):
        self.dthread = threading.Thread(target=self.worker.run, daemon=True)
        self.dthread.start()
