import json
import threading

from core.decorators import instance, event, timerevent, setting
from core.logger import Logger
from core.setting_types import ColorSettingType, TextSettingType
from .websocket_relay_worker import WebsocketRelayWorker


@instance()
class WebsocketRelayController:
    RELAY_HUB_SOURCE = "websocket_relay"

    def __init__(self):
        self.dthread = None
        self.queue = []
        self.logger = Logger(__name__)
        self.worker = None

    def inject(self, registry):
        self.relay_hub_service = registry.get_instance("relay_hub_service")

    def start(self):
        self.relay_hub_service.register_relay(self.RELAY_HUB_SOURCE, self.handle_incoming_relay_message)

    @setting(name="websocket_relay_server_address", value="ws://localhost/subscribe/relay", description="The address of the websocket relay server")
    def websocket_relay_server_address(self):
        return TextSettingType(["ws://localhost/subscribe/relay"])

    @setting(name="websocket_relay_channel_color", value="#FFFF00", description="Color of the channel in websocket relay messages")
    def websocket_channel_color(self):
        return ColorSettingType()

    @setting(name="websocket_relay_message_color", value="#FCA712", description="Color of the message content in websocket relay messages")
    def websocket_message_color(self):
        return ColorSettingType()

    @setting(name="websocket_relay_sender_color", value="#00DE42", description="Color of the sender in websocket relay messages")
    def websocket_sender_color(self):
        return ColorSettingType()

    @timerevent(budatime="1s", description="Relay messages from websocket relay to the relay hub")
    def handle_queue_event(self, event_type, event_data):
        while self.queue:
            obj = self.queue.pop(0)
            if obj.type == "message":
                payload = obj.payload
                # message = ("[Relay] <channel_color>[%s]<end> <sender_color>%s<end>: <message_color>%s<end>" % (payload.channel, payload.sender.name, payload.message))\
                #     .replace("<channel_color>", self.websocket_channel_color().get_font_color())\
                #     .replace("<message_color>", self.websocket_message_color().get_font_color())\
                #     .replace("<sender_color>", self.websocket_sender_color().get_font_color())
                message = payload.message

                self.relay_hub_service.send_message(self.RELAY_HUB_SOURCE, obj.get("sender", None), message)

    @event(event_type="connect", description="Connect to Websocket relay on startup")
    def handle_connect_event(self, event_type, event_data):
        self.connect()

    def handle_incoming_relay_message(self, ctx):
        if self.worker:
            obj = json.dumps({"sender": ctx.sender,
                              "message": ctx.message,
                              "channel": None})
            self.worker.send_message(obj)

    def connect(self):
        self.worker = WebsocketRelayWorker(self.queue, self.websocket_relay_server_address().get_value())

        self.disconnect()
        self.dthread = threading.Thread(target=self.worker.run, daemon=True)
        self.dthread.start()

    def disconnect(self):
        # TODO
        pass
