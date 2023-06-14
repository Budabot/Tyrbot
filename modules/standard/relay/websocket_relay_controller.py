import hashlib
import json
import threading
import base64
import time

from core.decorators import instance, timerevent, event
from core.logger import Logger
from core.dict_object import DictObject
from core.setting_types import ColorSettingType, TextSettingType, HiddenSettingType, BooleanSettingType
from core.private_channel_service import PrivateChannelService
from modules.core.org_members.org_member_controller import OrgMemberController
from modules.standard.online.online_controller import OnlineController
from .aesgcm_wrapper import AESGCMWrapper


@instance()
class WebsocketRelayController:
    MESSAGE_SOURCE = "websocket_relay"

    AES_GCM_NONCE_LENGTH = 12

    def __init__(self):
        self.dthread = None
        self.queue = []
        self.logger = Logger(__name__)
        self.encrypter = None
        self.channels = {}

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.setting_service = registry.get_instance("setting_service")
        self.event_service = registry.get_instance("event_service")
        self.character_service = registry.get_instance("character_service")
        self.pork_service = registry.get_instance("pork_service")
        self.online_controller = registry.get_instance("online_controller")
        self.public_channel_service = registry.get_instance("public_channel_service")
        self.message_hub_service = registry.get_instance("message_hub_service")
        self.highway_websocket_controller = registry.get_instance("highway_websocket_controller")

    def pre_start(self):
        self.message_hub_service.register_message_source(self.MESSAGE_SOURCE)

    def start(self):
        self.message_hub_service.register_message_destination(self.MESSAGE_SOURCE,
                                                              self.handle_message_from_hub,
                                                              ["private_channel", "private_channel_update", "org_channel", "org_channel_update", "discord"],
                                                              [self.MESSAGE_SOURCE])

        self.setting_service.register(self.module_name, "relay_prefix", "", TextSettingType(allow_empty=True), "Name of this relay (if you don't want to use org or bot name)")
        self.setting_service.register(self.module_name, "websocket_relay_enabled", False, BooleanSettingType(), "Enable the websocket relay")

        self.setting_service.register(self.module_name, "websocket_relay_room", "", TextSettingType(allow_empty=True), "The name of the websocket room to join (must be the same on all bots)")
        self.setting_service.register(self.module_name, "websocket_relay_channel_color", "#FFFF00", ColorSettingType(), "Color of the channel in websocket relay messages")
        self.setting_service.register(self.module_name, "websocket_relay_message_color", "#FCA712", ColorSettingType(), "Color of the message content in websocket relay messages")
        self.setting_service.register(self.module_name, "websocket_relay_sender_color", "#00DE42", ColorSettingType(), "Color of the sender in websocket relay messages")
        self.setting_service.register(self.module_name, "websocket_encryption_key", "", HiddenSettingType(allow_empty=True), "An encryption key used to encrypt messages over a public websocket relay")

        self.setting_service.register_change_listener("websocket_relay_enabled", self.websocket_relay_update)
        self.setting_service.register_change_listener("websocket_encryption_key", self.websocket_relay_update)
        self.setting_service.register_change_listener("websocket_relay_room", self.websocket_relay_update)
        self.setting_service.register(self.module_name, "websocket_symbol", "#",
                                      TextSettingType(["!", "#", "*", "@", "$", "+", "-"]),
                                      "Symbol for websocket relay")
        self.setting_service.register(self.module_name, "websocket_symbol_method", "Always",
                                      TextSettingType(["Always", "with_symbol", "unless_symbol"]),
                                      "When to relay messages")

        for setting_name in ["websocket_relay_enabled", "websocket_encryption_key"]:
            self.websocket_relay_update(setting_name, None, self.setting_service.get(setting_name).get_value())

    def initialize_encrypter(self, password):
        if password:
            key = hashlib.sha256(password.encode("utf-8")).digest()
            self.encrypter = AESGCMWrapper(key, self.AES_GCM_NONCE_LENGTH)
        else:
            self.encrypter = None

    def handle_websocket_message(self, obj):
        if obj.type == "message":
            self.process_relay_message(obj.user, obj.body)
        elif obj.type == "room-info":
            if obj.room == self.setting_service.get("websocket_relay_room").get_value():
                self.send_relay_message({"type": "online_list_request"})
                self.send_relay_message(self.get_online_list_obj())
        elif obj.type == "leave":
            if obj.room == self.setting_service.get("websocket_relay_room").get_value():
                for channel in self.channels.get(obj.user, []):
                    self.online_controller.deregister_online_channel(channel)

                if obj.user in self.channels:
                    del self.channels[obj.user]
        elif obj == self.highway_websocket_controller.DISCONNECT_OBJ:
            for channels in self.channels.values():
                for channel in channels:
                    self.online_controller.deregister_online_channel(channel)

    @event(PrivateChannelService.JOINED_PRIVATE_CHANNEL_EVENT, "Send to websocket relay when someone joins private channel", is_system=True, is_enabled=False)
    def private_channel_joined_event(self, event_type, event_data):
        self.send_relay_event(event_data.char_id, "logon", "private_channel")

    @event(PrivateChannelService.LEFT_PRIVATE_CHANNEL_EVENT, "Send to websocket relay when someone joins private channel", is_system=True, is_enabled=False)
    def private_channel_left_event(self, event_type, event_data):
        self.send_relay_event(event_data.char_id, "logoff", "private_channel")

    @event(OrgMemberController.ORG_MEMBER_LOGON_EVENT, "Send to websocket relay when org member logs on", is_system=True, is_enabled=False)
    def org_member_logon_event(self, event_type, event_data):
        self.send_relay_event(event_data.char_id, "logon", "org_channel")

    @event(OrgMemberController.ORG_MEMBER_LOGOFF_EVENT, "Send to websocket relay when org member logs off", is_system=True, is_enabled=False)
    def org_member_logoff_event(self, event_type, event_data):
        self.send_relay_event(event_data.char_id, "logoff", "org_channel")

    def decrypt_and_decode(self, message):
        try:
            if self.encrypter:
                decoded_message = base64.decodebytes(message.encode("utf-8"))
                message = self.encrypter.decrypt(decoded_message).decode("utf-8")
            return DictObject(json.loads(message))
        except Exception as e:
            self.logger.error(f"Error processing incoming message from websocket relay: '{message}'", e)

    def process_relay_message(self, client_id, message):
        obj = self.decrypt_and_decode(message)
        obj_type = obj.get("type") if obj else None

        if obj_type == "message":
            channel = self.get_channel_name(obj.source)

            message = ""
            message += "[%s] " % self.setting_service.get("websocket_relay_channel_color").format_text(channel)
            if obj.user:
                message += "%s: " % self.setting_service.get("websocket_relay_sender_color").format_text(obj.user.name)
            message += self.setting_service.get("websocket_relay_message_color").format_text(obj.message)

            self.message_hub_service.send_message(self.MESSAGE_SOURCE, None, None, message)
        elif obj_type == "logon":
            self.add_online_char(obj.user.id, obj.user.name, obj.source, client_id)
        elif obj_type == "logoff":
            self.rem_online_char(obj.user.id, obj.source)
        elif obj_type == "online_list":
            for online_obj in obj.online:
                if online_obj.source.type not in ["org", "priv"]:
                    continue

                channel = self.get_channel_name(online_obj.source)
                self.db.exec("DELETE FROM online WHERE channel = ?", [channel])
                for user in online_obj.users:
                    self.add_online_char(user.id, user.name, online_obj.source, client_id)
        elif obj_type == "online_list_request":
            self.send_relay_message(self.get_online_list_obj())
        else:
            self.logger.info(f"Unknown message type from websocket relay: {obj if obj else message}")

    def get_online_list_obj(self):
        sources = []
        for channel in [OnlineController.ORG_CHANNEL, OnlineController.PRIVATE_CHANNEL]:
            # TODO is this necessary?
            # if not an org bot, skip ORG_CHANNEL
            # if channel == OnlineController.ORG_CHANNEL and not self.public_channel_service.get_org_id():
            #    continue

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

    def add_online_char(self, char_id, name, source, client_id):
        # TODO how to handle chars not on current server
        if not char_id or (source.server and source.server != self.bot.dimension):
            return

        self.pork_service.load_character_info(char_id, name)
        channel = self.get_channel_name(source)
        if client_id not in self.channels:
            self.channels[client_id] = []
        if channel not in self.channels[client_id]:
            self.online_controller.register_online_channel(channel)
            self.channels[client_id].append(channel)

        self.db.exec("INSERT INTO online (char_id, afk_dt, afk_reason, channel, dt) VALUES (?, ?, ?, ?, ?)",
                     [char_id, 0, "", channel, int(time.time())])

    def rem_online_char(self, char_id, source):
        channel = self.get_channel_name(source)
        self.db.exec("DELETE FROM online WHERE char_id = ? AND channel = ?", [char_id, channel])

    def send_relay_message(self, message):
        if self.highway_websocket_controller.worker:
            message = json.dumps(message)
            if self.encrypter:
                message = base64.encodebytes(self.encrypter.encrypt(message.encode("utf-8"))).decode("utf-8")
            obj = json.dumps({"type": "message", "room": self.setting_service.get("websocket_relay_room").get_value(), "body": message})
            self.highway_websocket_controller.send_message(obj)

    def handle_message_from_hub(self, ctx):
        if self.highway_websocket_controller.worker:
            method = self.setting_service.get_value("websocket_symbol_method")
            symbol = self.setting_service.get_value("websocket_symbol")
            message = ctx.message or ctx.formatted_message

            if method == "unless_symbol" and message.startswith(symbol):
                return
            elif method == "with_symbol":
                if not message.startswith(symbol):
                    return
                else:
                    # trim symbol from message
                    message = message[len(symbol):]

            obj = {"user": self.create_user_obj(ctx.sender),
                   "message": message,
                   "type": "message",
                   "source": self.create_source_obj(ctx.source)}
            self.send_relay_message(obj)

    def websocket_relay_update(self, setting_name, old_value, new_value):
        if setting_name == "websocket_relay_enabled":
            event_handlers = [self.private_channel_joined_event, self.private_channel_left_event,
                              self.org_member_logon_event, self.org_member_logoff_event]
            for handler in event_handlers:
                event_handler = self.util.get_handler_name(handler)
                event_base_type, event_sub_type = self.event_service.get_event_type_parts(handler.event.event_type)
                self.event_service.update_event_status(event_base_type, event_sub_type, event_handler, 1 if new_value else 0)

            if old_value:
                self.highway_websocket_controller.unregister_room_callback(self.setting_service.get("websocket_relay_room").get_value(), self.handle_websocket_message)

            if new_value:
                self.highway_websocket_controller.register_room_callback(self.setting_service.get("websocket_relay_room").get_value(), self.handle_websocket_message)
        elif setting_name == "websocket_encryption_key":
            self.initialize_encrypter(new_value)
        elif setting_name == "websocket_relay_room":
            if self.setting_service.get("websocket_relay_enabled").get_value():
                self.highway_websocket_controller.unregister_room_callback(old_value, self.handle_websocket_message)
                self.highway_websocket_controller.register_room_callback(new_value, self.handle_websocket_message)

    def get_channel_name(self, source):
        channel_name = source.get("label") or source.get("name") or "Unknown Relay"
        if source.get("channel"):
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
        conn = self.bot.get_temp_conn()
        org_name = conn.org_name

        if source == "private_channel" or source == "private_channel_update" or source == OnlineController.PRIVATE_CHANNEL:
            if org_name:
                channel = "Guest"
            else:
                channel = ""
        elif org_name and (source == "org_channel" or source == "org_channel_update" or source == OnlineController.ORG_CHANNEL):
            channel = ""
        else:
            channel = source.capitalize()

        channel_type = source
        if source == "private_channel" or source == OnlineController.PRIVATE_CHANNEL:
            channel_type = "priv"
        elif source == "org_channel" or source == OnlineController.ORG_CHANNEL:
            channel_type = "org"

        return {
            "name": org_name or conn.get_char_name(),
            "label": self.setting_service.get("relay_prefix").get_value() or None,
            "channel": channel,
            "type": channel_type,
            "server": self.bot.dimension
        }
