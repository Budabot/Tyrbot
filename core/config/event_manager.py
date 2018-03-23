from core.decorators import instance
from core.registry import Registry
from core.logger import Logger
import collections


@instance()
class EventManager:
    def __init__(self):
        self.handlers = collections.defaultdict(list)
        self.logger = Logger("event_manager")
        self.event_types = []

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")

    def start(self):
        self.db.load_sql_file("./core/config/event_config.sql")
        self.db.exec("UPDATE event_config SET verified = 0")

    def post_start(self):
        # process decorators
        for _, inst in Registry.get_all_instances().items():
            for name, method in inst.__class__.__dict__.items():
                if hasattr(method, "event"):
                    event_type, description = getattr(method, "event")
                    handler = getattr(inst, name)
                    module = self.util.get_module_name(handler)
                    self.register(handler, event_type, description, module)

        self.db.exec("DELETE FROM event_config WHERE verified = 0")

    def register_event_type(self, event_type):
        event_type = event_type.lower()

        if event_type in self.event_types:
            self.logger.error("Could not register event type '%s': event type already registered"
                              % event_type)
            return

        self.logger.debug("Registering event type '%s'" % event_type)
        self.event_types.append(event_type)

    def register(self, handler, event_type, description, module):
        event_type_base, event_sub_type = self.get_event_type_parts(event_type)
        module = module.lower()
        handler_name = self.util.get_handler_name(handler)

        if event_type_base not in self.event_types:
            self.logger.error("Could not register handler '%s' for event type '%s': event type does not exist"
                              % (handler_name, event_type))
            return

        row = self.db.query_single("SELECT 1 "
                                   "FROM event_config WHERE event_type = ? AND handler = ?",
                                   [event_type, handler_name])

        if row is None:
            # add new event config
            self.db.exec(
                "INSERT INTO event_config (event_type, handler, description, module, enabled, verified) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                [event_type, handler_name, description, module, 1, 1])
        else:
            # mark command as verified
            self.db.exec(
                "UPDATE event_config SET verified = ?, module = ?, description = ? "
                "WHERE event_type = ? AND handler = ?",
                [1, module, description, event_type, handler_name])

        # load command handler
        self.handlers[event_type].append({"handler": handler, "name": handler_name})

    def fire_event(self, event_type, event_data=None):
        event_type_base, event_sub_type = self.get_event_type_parts(event_type)

        if event_type_base not in self.event_types:
            self.logger.error("Could not fire event type '%s': event type does not exist" % event_type)
            return

        for handler in self.handlers[event_type]:
            row = self.db.query_single("SELECT enabled FROM event_config "
                                       "WHERE event_type = ? AND handler = ?",
                                       [event_type, handler["name"]])
            if row is None:
                self.logger.error("Could not find event configuration for event type '%s' and handler '%s'"
                                  % (event_type, handler["name"]))
                return

            if row.enabled == 1:
                handler["handler"](event_type, event_data)

    def get_event_type_parts(self, event_type):
        arr = event_type.lower().split(":", 1)
        return arr[0], arr[1] if len(arr) > 1 else ""

    def check_for_timer_events(self):
        pass
