import json
import threading
import base64
import string
import random

from core.decorators import instance, event, timerevent, setting
from core.logger import Logger
from core.dict_object import DictObject
from core.setting_types import ColorSettingType, TextSettingType, HiddenSettingType, BooleanSettingType
from .websocket_relay_worker import WebsocketRelayWorker
from core.registry import Registry
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


@instance()
class WebsocketRelayController:
    RELAY_HUB_SOURCE = "websocket_relay"

    def __init__(self):
        self.dthread = None
        self.queue = []
        self.logger = Logger(__name__)
        self.worker = None
        self.encrypter = None

    def inject(self, registry):
        self.relay_hub_service = registry.get_instance("relay_hub_service")
        self.util = registry.get_instance("util")
        self.setting_service = registry.get_instance("setting_service")
        self.event_service = registry.get_instance("event_service")

    def start(self):
        self.relay_hub_service.register_relay(self.RELAY_HUB_SOURCE, self.handle_incoming_relay_message)
        if self.websocket_encryption_key().get_value():
            password = self.websocket_encryption_key().get_value().encode("utf-8")
            salt = b"tyrbot"  # using hard-coded salt is less secure as it nullifies the function of the salt and allows for rainbow attacks
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,)
            key = base64.urlsafe_b64encode(kdf.derive(password))
            self.encrypter = Fernet(key)
            
        self.setting_service.register_change_listener("websocket_relay_enabled", self.websocket_relay_status_changed)

    @setting(name="websocket_relay_enabled", value=False, description="Enable or disable the websocket relay")
    def websocket_relay_enabled(self):
        return BooleanSettingType()

    @setting(name="websocket_relay_server_address", value="ws://localhost/subscribe/relay", description="The address of the websocket relay server",
             extended_description="All bots on the relay must connect to the same server and channel. If using the public relay server, use a unique channel name. Example: ws://relay.jkbff.com/subscribe/unique123 (<highlight>relay.jkbff.com<end> is the server and <highlight>unique123<end> is the channel)")
    def websocket_relay_server_address(self):
        return TextSettingType(["ws://localhost/subscribe/relay", "ws://relay.jkbff.com/subscribe/relay"])

    @setting(name="websocket_relay_channel_color", value="#FFFF00", description="Color of the channel in websocket relay messages")
    def websocket_channel_color(self):
        return ColorSettingType()

    @setting(name="websocket_relay_message_color", value="#FCA712", description="Color of the message content in websocket relay messages")
    def websocket_message_color(self):
        return ColorSettingType()

    @setting(name="websocket_relay_sender_color", value="#00DE42", description="Color of the sender in websocket relay messages")
    def websocket_sender_color(self):
        return ColorSettingType()

    @setting(name="websocket_encryption_key", value="", description="An encryption key used to encrypt messages over a public websocket relay",
             extended_description="")
    def websocket_encryption_key(self):
        return HiddenSettingType()

    @timerevent(budatime="1s", description="Relay messages from websocket relay to the relay hub", is_hidden=True)
    def handle_queue_event(self, event_type, event_data):
        while self.queue:
            obj = DictObject(json.loads(self.queue.pop(0)))
            if obj.type == "message":
                payload = obj.payload
                if self.encrypter:
                    payload = self.encrypter.decrypt(payload.encode('utf-8'))
                payload = DictObject(json.loads(payload))
                # message = ("[Relay] <channel_color>[%s]<end> <sender_color>%s<end>: <message_color>%s<end>" % (payload.channel, payload.sender.name, payload.message))\
                #     .replace("<channel_color>", self.websocket_channel_color().get_font_color())\
                #     .replace("<message_color>", self.websocket_message_color().get_font_color())\
                #     .replace("<sender_color>", self.websocket_sender_color().get_font_color())
                message = payload.message

                self.relay_hub_service.send_message(self.RELAY_HUB_SOURCE, obj.get("sender", None), message)

    @event(event_type="connect", description="Connect to Websocket relay on startup", is_hidden=True)
    def handle_connect_event(self, event_type, event_data):
        self.connect()

    def handle_incoming_relay_message(self, ctx):
        if self.worker:
            obj = json.dumps({"sender": ctx.sender,
                              "message": ctx.message,
                              "channel": None})
            if self.encrypter:
                obj = self.encrypter.encrypt(obj.encode('utf-8'))
            self.worker.send_message(obj)

    def connect(self):
        self.disconnect()
        
        self.worker = WebsocketRelayWorker(self.queue, self.websocket_relay_server_address().get_value())
        self.dthread = threading.Thread(target=self.worker.run, daemon=True)
        self.dthread.start()

    def disconnect(self):
        if self.worker:
            self.worker.close()
            self.worker = None
            self.dthread.join()
            self.dthread = None

    def websocket_relay_status_changed(self, name, old_value, new_value):
        for handler in [self.handle_connect_event, self.handle_queue_event]:
            event_handler = self.util.get_handler_name(handler)
            event_base_type, event_sub_type = self.event_service.get_event_type_parts(handler.event[0])
            self.event_service.update_event_status(event_base_type, event_sub_type, event_handler, 1 if new_value else 0)

        if new_value:
            self.connect()
        else:
            self.disconnect()
