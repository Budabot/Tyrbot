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
from .websocket_relay_worker import WebsocketRelayWorker


@instance()
class HighwayWebsocketController:
    DISCONNECT_OBJ = DictObject({"type": "disconnect"})

    def __init__(self):
        self.logger = Logger(__name__)
        self.dthread = None
        self.worker = None
        self.callbacks = {}

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.setting_service = registry.get_instance("setting_service")
        self.event_service = registry.get_instance("event_service")

    def start(self):
        self.setting_service.register(self.module_name, "websocket_relay_server_address", "wss://ws.nadybot.org",
                                      TextSettingType(["wss://ws.nadybot.org"]),
                                      "The address of the websocket relay server",
                                      "Point this to a running instance of https://github.com/Nadybot/highway")

    def register_room_callback(self, room_name, callback_func):
        print("register room: " + room_name)
        callbacks = self.callbacks.get(room_name, [])
        callbacks.append(callback_func)

        if self.worker:
            # if room isn't already joined, join room
            if not self.callbacks.get(room_name):
                self.worker.send_message(json.dumps({"type": "join", "room": room_name}))
        else:
            self.connect()

        self.callbacks[room_name] = callbacks

    def unregister_room_callback(self, room_name, callback_func):
        callbacks = self.callbacks.get(room_name, [])
        for idx, callback in enumerate(callbacks):
            if callback == callback_func:
                del callbacks[idx]

        if callbacks:
            self.callbacks[room_name] = callbacks
        elif room_name in self.callbacks:
            del self.callbacks[room_name]
            # if room is already joined and worker is connected, leave room
            if self.worker:
                self.worker.send_message(json.dumps({"type": "leave", "room": room_name}))

        if not self.callbacks:
            self.disconnect()

    @timerevent(budatime="1s", description="Process messages from websocket", is_system=True, is_enabled=True)
    def handle_queue_event(self, event_type, event_data):
        if not self.worker:
            return
    
        obj = self.worker.get_message_from_queue()
        while obj:
            room = obj.get("room")
            if room:
                for callback in self.callbacks.get(room, []):
                    callback(obj)

            if obj.type == "hello":
                for room in self.callbacks.keys():
                    self.worker.send_message(json.dumps({"type": "join", "room": room}))
            elif obj.type == "failure":
                self.logger.error(obj)
            elif obj.type == "disconnect":
                for rooms in self.callbacks:
                    for callback in rooms:
                        callback(obj)

            obj = self.worker.get_message_from_queue()

    @timerevent(budatime="30s", description="Ensure the bot is connected to websocket relay", is_system=True, is_enabled=True, run_at_startup=True)
    def handle_connect_event(self, event_type, event_data):
        if not self.worker or not self.dthread.is_alive():
            if self.callbacks:
                self.connect()
        else:
            self.worker.send_ping()

    def send_message(self, obj):
        if self.worker:
            self.worker.send_message(obj)

    def connect(self):
        self.disconnect()

        # TODO enable events

        self.worker = WebsocketRelayWorker(self.setting_service.get("websocket_relay_server_address").get_value(), f"Tyrbot {self.bot.version}")
        self.dthread = threading.Thread(target=self.worker.run, daemon=True)
        self.dthread.start()

    def disconnect(self):
        if self.worker:
            self.worker.close()
            self.worker = None
            self.dthread.join()
            self.dthread = None

            # TODO disable events

            for rooms in self.callbacks.values():
                for callback in rooms:
                    callback(self.DISCONNECT_OBJ)

    def websocket_relay_update(self, setting_name, old_value, new_value):
        if setting_name == "websocket_relay_server_address":
            if self.setting_service.get("websocket_relay_enabled").get_value():
                self.connect()
