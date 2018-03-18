from core.decorators import instance
from core.access_manager import AccessManager
from core.aochat import server_packets
from core.character_manager import CharacterManager
from core.setting_manager import SettingManager
from core.registry import Registry
from core.logger import Logger
import collections
import re


@instance()
class EventManager:
    def __init__(self):
        self.db = None
        self.handlers = collections.defaultdict(list)
        self.logger = Logger("event_manager")
        self.event_types = ["connect"]

    def inject(self, registry):
        self.db = registry.get_instance("db")

    def start(self):
        self.db.load_sql_file("./core/config/event_config.sql")
        self.db.exec("UPDATE event_config SET verified = 0")

    def post_start(self):
        # process decorators
        for _, inst in Registry.get_all_instances().items():
            for name, method in inst.__class__.__dict__.items():
                if hasattr(method, "event"):
                    event_type, = getattr(method, "event")
                    self.register(getattr(inst, name), event_type)

        self.db.exec("DELETE FROM event_config WHERE verified = 0")

    def register_event_type(self, event_type):
        if event_type in self.event_types:
            self.logger.error("Could not register event type '%s': event type already registered"
                              % event_type)
            return

        self.logger.debug("Registering event type '%s'" % event_type)
        self.event_types.append(event_type)

    def register(self, handler, event_type):
        handler_name = self.get_handler_name(handler)

        if event_type not in self.event_types:
            self.logger.error("Could not register handler '%s' for event type '%s': event type does not exist"
                              % (handler_name, event_type))
            return

        row = self.db.query_single("SELECT event_type, handler, enabled, verified "
                                   "FROM event_config WHERE event_type = ? AND handler = ?",
                                   [event_type, handler_name])

        if row is None:
            # add new event config
            self.db.exec(
                "INSERT INTO event_config (event_type, handler, enabled, verified) VALUES "
                "(?, ?, ?, ?)",
                [event_type, handler_name, 1, 1])
        else:
            # mark command as verified
            self.db.exec(
                "UPDATE event_config SET verified = ? WHERE event_type = ? AND handler = ?",
                [1, event_type, handler_name])

        # load command handler
        self.handlers[event_type].append({"handler": handler, "name": handler_name})

    def get_handler_name(self, handler):
        return handler.__module__ + "." + handler.__qualname__

    def fire_event(self, event_type, event_data=None):
        if event_type not in self.event_types:
            self.logger.error("Could not fire event type '%s': event type does not exist" % event_type)
            return

        for handler in self.handlers[event_type]:
            row = self.db.query_single("SELECT enabled FROM event_config WHERE event_type = ? AND handler = ?",
                                       [event_type, handler["name"]])
            if row is None:
                self.logger.error("Could not find event configuration for event type '%s' and handler '%s'"
                                  % (event_type, handler["name"]))
                return

            if row.enabled == 1:
                handler["handler"](event_type, event_data)
