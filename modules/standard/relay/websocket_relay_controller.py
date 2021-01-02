import json
import threading
import base64
import time

from core.decorators import instance, timerevent, setting, event
from core.logger import Logger
from core.dict_object import DictObject
from core.setting_types import ColorSettingType, TextSettingType, HiddenSettingType, BooleanSettingType
from core.private_channel_service import PrivateChannelService
from modules.core.org_members.org_member_controller import OrgMemberController
from .websocket_relay_worker import WebsocketRelayWorker
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


@instance()
class WebsocketRelayController:
    MESSAGE_SOURCE = "websocket_relay"

    def __init__(self):
        self.dthread = None
        self.queue = []
        self.logger = Logger(__name__)
        self.worker = None
        self.encrypter = None
        self.channels = []

    def inject(self, registry):
        self.message_hub_service = registry.get_instance("message_hub_service")
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.setting_service = registry.get_instance("setting_service")
        self.event_service = registry.get_instance("event_service")
        self.relay_controller = registry.get_instance("relay_controller")
        self.character_service = registry.get_instance("character_service")
        self.pork_service = registry.get_instance("pork_service")
        self.online_controller = registry.get_instance("online_controller")

    def start(self):
        self.message_hub_service.register_message_source(self.MESSAGE_SOURCE, self.handle_message_from_hub)

        self.initialize_encrypter(self.websocket_encryption_key().get_value())
            
        self.setting_service.register_change_listener("websocket_relay_enabled", self.websocket_relay_update)
        self.setting_service.register_change_listener("websocket_relay_server_address", self.websocket_relay_update)
        self.setting_service.register_change_listener("websocket_encryption_key", self.websocket_relay_update)

    def initialize_encrypter(self, password):
        if password:
            salt = b"tyrbot"  # using hard-coded salt is less secure as it nullifies the function of the salt and allows for rainbow attacks
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=10000,)
            key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
            self.encrypter = Fernet(key)
        else:
            self.encrypter = None

    @setting(name="websocket_relay_enabled", value=False, description="Enable the websocket relay")
    def websocket_relay_enabled(self):
        return BooleanSettingType()

    @setting(name="websocket_relay_server_address", value="ws://localhost/subscribe/relay", description="The address of the websocket relay server",
             extended_description="All bots on the relay must connect to the same server and channel. If using the public relay server, use a unique channel name. Example: ws://relay.jkbff.com/subscribe/unique123 (<highlight>relay.jkbff.com<end> is the server and <highlight>unique123<end> is the channel)")
    def websocket_relay_server_address(self):
        return TextSettingType(["ws://localhost/subscribe/relay", "wss://relay.jkbff.com/subscribe/relay"])

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
        return HiddenSettingType(allow_empty=True)

    @timerevent(budatime="1s", description="Relay messages from websocket relay to the relay hub", is_hidden=True, is_enabled=False)
    def handle_queue_event(self, event_type, event_data):
        while self.queue:
            obj = self.queue.pop(0)
            if obj.type == "message":  # TODO "content"
                payload = obj.payload
                self.process_relay_message(payload)
            elif obj.type == "ping":
                return_obj = json.dumps({"type": "ping", "payload": obj.payload})
                self.worker.send_message(return_obj)

    @timerevent(budatime="1m", description="Ensure the bot is connected to websocket relay", is_hidden=True, is_enabled=False)
    def handle_connect_event(self, event_type, event_data):
        if not self.worker or not self.dthread.is_alive():
            self.connect()

    @event(PrivateChannelService.JOINED_PRIVATE_CHANNEL_EVENT, "Send to websocket relay when someone joins private channel", is_hidden=True, is_enabled=False)
    def private_channel_joined_event(self, event_type, event_data):
        self.send_relay_event(event_data.char_id, "logon")

    @event(PrivateChannelService.LEFT_PRIVATE_CHANNEL_EVENT, "Send to websocket relay when someone joins private channel", is_hidden=True, is_enabled=False)
    def private_channel_left_event(self, event_type, event_data):
        self.send_relay_event(event_data.char_id, "logoff")

    @event(OrgMemberController.ORG_MEMBER_LOGON_EVENT, "Send to websocket relay when org member logs on", is_hidden=True, is_enabled=False)
    def org_member_logon_event(self, event_type, event_data):
        self.send_relay_event(event_data.char_id, "logon")

    @event(OrgMemberController.ORG_MEMBER_LOGOFF_EVENT, "Send to websocket relay when org member logs off", is_hidden=True, is_enabled=False)
    def org_member_logoff_event(self, event_type, event_data):
        self.send_relay_event(event_data.char_id, "logoff")

    @event(OrgMemberController.ORG_MEMBER_REMOVED_EVENT, "Send to websocket relay when org member is removed", is_hidden=True, is_enabled=False)
    def org_member_removed_event(self, event_type, event_data):
        self.send_relay_event(event_data.char_id, "logoff")

    def process_relay_message(self, message):
        if self.encrypter:
            message = self.encrypter.decrypt(message.encode('utf-8'))
        obj = DictObject(json.loads(message))

        if obj.type == "message":
            message = ""
            message += "%s[%s]<end> " % (self.websocket_channel_color().get_font_color(), obj.channel)
            if obj.sender:
                message += "%s%s<end>: " % (self.websocket_sender_color().get_font_color(), obj.sender.name)
            message += "%s%s<end>" % (self.websocket_message_color().get_font_color(), obj.message)

            self.message_hub_service.send_message(self.MESSAGE_SOURCE, obj.get("sender", None), obj.message, message)
        elif obj.type == "logon":
            self.add_online_char(obj.sender.char_id, obj.channel)
        elif obj.type == "logoff":
            self.rem_online_char(obj.sender.char_id, obj.channel)
        elif obj.type == "online_list":
            self.db.exec("DELETE FROM online WHERE channel = ?", [obj.channel])
            for sender in obj.members:
                self.add_online_char(sender.char_id, obj.channel)
        elif obj.type == "online_list_request":
            # TODO
            print("Got " + obj.type)

    def send_relay_event(self, char_id, event_type):
        char_name = self.character_service.resolve_char_to_name(char_id)
        obj = json.dumps({"sender": {"char_id": char_id,
                                     "name": char_name},
                          "type": event_type,
                          "channel": self.relay_controller.get_org_channel_prefix()})
        self.send_relay_message(obj)

    def add_online_char(self, char_id, channel):
        self.pork_service.load_character_info(char_id)
        if channel not in self.channels:
            self.online_controller.register_online_channel(channel)
            self.channels.append(channel)
        self.db.exec("INSERT INTO online (char_id, afk_dt, afk_reason, channel, dt) VALUES (?, ?, ?, ?, ?)",
                     [char_id, 0, "", channel, int(time.time())])
        
    def rem_online_char(self, char_id, channel):
        self.db.exec("DELETE FROM online WHERE char_id = ? AND channel = ?", [char_id, channel])
        
    def send_relay_message(self, message):
        if self.worker:
            if self.encrypter:
                message = self.encrypter.encrypt(message.encode('utf-8'))
            obj = json.dumps({"type": "message", "payload": message})
            self.worker.send_message(obj)

    def handle_message_from_hub(self, ctx):
        if self.worker:
            obj = json.dumps({"sender": ctx.sender,
                              "message": ctx.message,
                              "type": "message",
                              "channel": self.relay_controller.get_org_channel_prefix()})
            self.send_relay_message(obj)

    def connect(self):
        self.disconnect()

        self.worker = WebsocketRelayWorker(self.queue, self.websocket_relay_server_address().get_value())
        self.dthread = threading.Thread(target=self.worker.run, daemon=True)
        self.dthread.start()

    def disconnect(self):
        for channel in self.channels:
            self.db.exec("DELETE FROM online WHERE channel = ?", [channel])

        if self.worker:
            self.worker.close()
            self.worker = None
            self.dthread.join()
            self.dthread = None

    def websocket_relay_update(self, setting_name, old_value, new_value):
        if setting_name == "websocket_relay_enabled":
            event_handlers = [self.handle_connect_event, self.handle_queue_event, self.private_channel_joined_event, self.private_channel_left_event,
                self.org_member_logon_event, self.org_member_logoff_event, self.org_member_removed_event]
            for handler in event_handlers:
                event_handler = self.util.get_handler_name(handler)
                event_base_type, event_sub_type = self.event_service.get_event_type_parts(handler.event[0])
                self.event_service.update_event_status(event_base_type, event_sub_type, event_handler, 1 if new_value else 0)

            if new_value and self.bot.is_ready():
                self.connect()
            else:
                self.disconnect()
        elif setting_name == "websocket_relay_server_address":
            if self.setting_service.get("websocket_relay_enabled").get_value():
                self.connect()
        elif setting_name == "websocket_encryption_key":
            self.initialize_encrypter(new_value)
            if self.setting_service.get("websocket_relay_enabled").get_value():
                self.connect()
