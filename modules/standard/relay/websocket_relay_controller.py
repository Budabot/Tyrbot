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
from modules.standard.online.online_controller import OnlineController
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
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.setting_service = registry.get_instance("setting_service")
        self.event_service = registry.get_instance("event_service")
        self.relay_controller = registry.get_instance("relay_controller")
        self.character_service = registry.get_instance("character_service")
        self.pork_service = registry.get_instance("pork_service")
        self.online_controller = registry.get_instance("online_controller")
        self.public_channel_service = registry.get_instance("public_channel_service")
        self.message_hub_service = registry.get_instance("message_hub_service")

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

    @timerevent(budatime="1s", description="Relay messages from websocket relay to the internal message hub", is_hidden=True, is_enabled=False)
    def handle_queue_event(self, event_type, event_data):
        while self.queue:
            obj = self.queue.pop(0)
            if obj.type == "message":  # TODO "content"
                payload = obj.payload
                self.process_relay_message(payload)
            elif obj.type == "ping":
                return_obj = json.dumps({"type": "ping", "payload": obj.payload})
                self.worker.send_message(return_obj)
            elif obj.type == "connected":
                # TODO how to handle when a bot disconnects from the relay who had online members
                self.send_relay_message({"type": "online_list_request"})
                self.send_relay_message(self.get_online_list_obj())

    @timerevent(budatime="1m", description="Ensure the bot is connected to websocket relay", is_hidden=True, is_enabled=False)
    def handle_connect_event(self, event_type, event_data):
        if not self.worker or not self.dthread.is_alive():
            self.connect()

    @event(PrivateChannelService.JOINED_PRIVATE_CHANNEL_EVENT, "Send to websocket relay when someone joins private channel", is_hidden=True, is_enabled=False)
    def private_channel_joined_event(self, event_type, event_data):
        self.send_relay_event(event_data.char_id, "logon", "private_channel")

    @event(PrivateChannelService.LEFT_PRIVATE_CHANNEL_EVENT, "Send to websocket relay when someone joins private channel", is_hidden=True, is_enabled=False)
    def private_channel_left_event(self, event_type, event_data):
        self.send_relay_event(event_data.char_id, "logoff", "private_channel")

    @event(OrgMemberController.ORG_MEMBER_LOGON_EVENT, "Send to websocket relay when org member logs on", is_hidden=True, is_enabled=False)
    def org_member_logon_event(self, event_type, event_data):
        self.send_relay_event(event_data.char_id, "logon", "org_channel")

    @event(OrgMemberController.ORG_MEMBER_LOGOFF_EVENT, "Send to websocket relay when org member logs off", is_hidden=True, is_enabled=False)
    def org_member_logoff_event(self, event_type, event_data):
        self.send_relay_event(event_data.char_id, "logoff", "org_channel")

    @event(OrgMemberController.ORG_MEMBER_REMOVED_EVENT, "Send to websocket relay when org member is removed", is_hidden=True, is_enabled=False)
    def org_member_removed_event(self, event_type, event_data):
        self.send_relay_event(event_data.char_id, "logoff", "org_channel")

    def process_relay_message(self, message):
        if self.encrypter:
            message = self.encrypter.decrypt(message.encode('utf-8'))
        obj = DictObject(json.loads(message))

        if obj.type == "message":
            channel = self.get_channel_name(obj.source)

            message = ""
            message += "%s[%s]<end> " % (self.websocket_channel_color().get_font_color(), channel)
            if obj.user:
                message += "%s%s<end>: " % (self.websocket_sender_color().get_font_color(), obj.user.name)
            message += "%s%s<end>" % (self.websocket_message_color().get_font_color(), obj.message)

            self.message_hub_service.send_message(self.MESSAGE_SOURCE, obj.get("user", None), obj.message, message)
        elif obj.type == "logon":
            self.add_online_char(obj.user.id, obj.user.name, obj.source)
        elif obj.type == "logoff":
            self.rem_online_char(obj.user.id, obj.source)
        elif obj.type == "online_list":
            for online_obj in obj.online:
                if online_obj.source.type not in ["org", "priv"]:
                    continue

                channel = self.get_channel_name(online_obj.source)
                self.db.exec("DELETE FROM online WHERE channel = ?", [channel])
                for user in online_obj.users:
                    self.add_online_char(user.id, user.name, online_obj.source)
        elif obj.type == "online_list_request":
            self.send_relay_message(self.get_online_list_obj())

    def get_online_list_obj(self):
        sources = []
        for channel in [OnlineController.ORG_CHANNEL, OnlineController.PRIVATE_CHANNEL]:
            # if not an org bot, skip ORG_CHANNEL
            if channel == OnlineController.ORG_CHANNEL and not self.public_channel_service.get_org_id():
                continue

            sql = """
                SELECT
                    o.char_id AS id,
                    COALESCE(p.name, o.char_id) AS name
                FROM online o
                LEFT JOIN player p ON (o.char_id = p.char_id)
                WHERE channel = ?
            """
            data = self.db.query(sql, [channel])

            sources.append({
                "source": self.create_source_obj(channel),
                "users": data
            })

        return {
            "type": "online_list",
            "online": sources
        }

    def send_relay_event(self, char_id, event_type, source):
        char_name = self.character_service.resolve_char_to_name(char_id)
        obj = {"user": {"id": char_id,
                        "name": char_name},
               "type": event_type,
               "source": self.create_source_obj(source)}
        self.send_relay_message(obj)

    def add_online_char(self, char_id, name, source):
        # TODO how to handle chars not on current server
        if not char_id or (source.server and source.server != self.bot.dimension):
            return

        self.pork_service.load_character_info(char_id, name)
        channel = self.get_channel_name(source)
        if channel not in self.channels:
            self.online_controller.register_online_channel(channel)
            self.channels.append(channel)

        self.db.exec("INSERT INTO online (char_id, afk_dt, afk_reason, channel, dt) VALUES (?, ?, ?, ?, ?)",
                     [char_id, 0, "", channel, int(time.time())])

    def rem_online_char(self, char_id, source):
        channel = self.get_channel_name(source)
        self.db.exec("DELETE FROM online WHERE char_id = ? AND channel = ?", [char_id, channel])

    def send_relay_message(self, message):
        if self.worker:
            message = json.dumps(message)
            if self.encrypter:
                message = self.encrypter.encrypt(message.encode('utf-8')).decode('utf-8')
            obj = json.dumps({"type": "message", "payload": message})
            self.worker.send_message(obj)

    def handle_message_from_hub(self, ctx):
        if self.worker:
            # TODO use relay_symbol to determine if message should be relayed or not

            obj = {"user": self.create_user_obj(ctx.sender),
                   "message": ctx.message or ctx.formatted_message,
                   "type": "message",
                   "source": self.create_source_obj(ctx.source)}
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

    def get_channel_name(self, source):
        channel_name = source.label or source.name
        if source.channel:
            channel_name += " " + source.channel
        return channel_name

    def create_user_obj(self, sender):
        if sender:
            return {
                "id": sender.get("char_id", None),
                "name": sender.name
            }
        else:
            return None

    def create_source_obj(self, source):
        org_name = self.public_channel_service.get_org_name()
        channel = ""
        if org_name:
            if source == "private_channel" or source == OnlineController.PRIVATE_CHANNEL:
                channel = "Guest"
        else:
            if source != "private_channel" and source != OnlineController.PRIVATE_CHANNEL:
                channel = source.capitalize()

        channel_type = source
        if source == "private_channel" or source == OnlineController.PRIVATE_CHANNEL:
            channel_type = "priv"
        elif source == "org_channel" or source == OnlineController.ORG_CHANNEL:
            channel_type = "org"

        return {
            "name": org_name or self.bot.char_name,
            "label": self.setting_service.get("relay_prefix").get_value() or "",
            "channel": channel,
            "type": channel_type,
            "server": self.bot.dimension
        }
