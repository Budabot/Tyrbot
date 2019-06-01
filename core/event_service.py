from core.decorators import instance
from core.registry import Registry
from core.logger import Logger
from __init__ import get_attrs
import time


@instance()
class EventService:
    def __init__(self):
        self.handlers = {}
        self.logger = Logger(__name__)
        self.event_types = []
        self.db_cache = {}

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")

    def pre_start(self):
        self.register_event_type("timer")

    def start(self):
        # process decorators
        for _, inst in Registry.get_all_instances().items():
            for name, method in get_attrs(inst).items():
                if hasattr(method, "event"):
                    event_type, description, is_hidden = getattr(method, "event")
                    handler = getattr(inst, name)
                    module = self.util.get_module_name(handler)
                    self.register(handler, event_type, description, module, is_hidden)

    def register_event_type(self, event_type):
        event_type = event_type.lower()

        if event_type in self.event_types:
            self.logger.error("Could not register event type '%s': event type already registered" % event_type)
            return

        self.logger.debug("Registering event type '%s'" % event_type)
        self.event_types.append(event_type)

    def is_event_type(self, event_base_type):
        return event_base_type in self.event_types

    def register(self, handler, event_type, description, module, is_hidden):
        event_base_type, event_sub_type = self.get_event_type_parts(event_type)
        module = module.lower()
        handler_name = self.util.get_handler_name(handler)
        is_hidden = 1 if is_hidden else 0

        if event_base_type not in self.event_types:
            self.logger.error("Could not register handler '%s' for event type '%s': event type does not exist" % (handler_name, event_type))
            return

        if not description:
            self.logger.warning("No description for event_type '%s' and handler '%s'" % (event_type, handler_name))

        row = self.db.query_single("SELECT 1 FROM event_config WHERE event_type = ? AND handler = ?",
                                   [event_base_type, handler_name])

        if row is None:
            # add new event commands
            self.db.exec(
                "INSERT INTO event_config (event_type, event_sub_type, handler, description, module, enabled, verified, is_hidden) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [event_base_type, event_sub_type, handler_name, description, module, 1, 1, is_hidden])

            if event_base_type == "timer":
                self.db.exec("INSERT INTO timer_event (event_type, event_sub_type, handler, next_run) VALUES (?, ?, ?, ?)",
                             [event_base_type, event_sub_type, handler_name, int(time.time())])
        else:
            # mark command as verified
            self.db.exec(
                "UPDATE event_config SET verified = ?, module = ?, description = ?, event_sub_type = ?, is_hidden = ? WHERE event_type = ? AND handler = ?",
                [1, module, description, event_sub_type, is_hidden, event_base_type, handler_name])

            if event_base_type == "timer":
                self.db.exec("UPDATE timer_event SET event_sub_type = ? WHERE event_type = ? AND handler = ?",
                             [event_sub_type, event_base_type, handler_name])

        # load command handler
        self.handlers[handler_name] = handler

    def fire_event(self, event_type, event_data=None):
        event_base_type, event_sub_type = self.get_event_type_parts(event_type)

        if event_base_type not in self.event_types:
            self.logger.error("Could not fire event type '%s': event type does not exist" % event_type)
            return

        data = self.get_handlers(event_base_type, event_sub_type)
        for row in data:
            self.call_handler(row.handler, event_type, event_data)

    def call_handler(self, handler_method, event_type, event_data):
        handler = self.handlers.get(handler_method, None)
        if not handler:
            self.logger.error("Could not find handler callback for event type '%s' and handler '%s'" % (event_type, handler_method))
            return

        try:
            handler(event_type, event_data)
        except Exception as e:
            self.logger.error("error processing event '%s'" % event_type, e)

    def get_event_type_parts(self, event_type):
        parts = event_type.lower().split(":", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        else:
            return parts[0], ""

    def get_event_type_key(self, event_base_type, event_sub_type):
        return event_base_type + ":" + event_sub_type

    def check_for_timer_events(self, current_timestamp):
        data = self.db.query("SELECT e.event_type, e.event_sub_type, e.handler, t.next_run FROM timer_event t "
                             "JOIN event_config e ON t.event_type = e.event_type AND t.handler = e.handler "
                             "WHERE t.next_run <= ? AND e.enabled = 1", [current_timestamp])
        for row in data:
            self.execute_timed_event(row, current_timestamp)

    def execute_timed_event(self, row, current_timestamp):
        event_type_key = self.get_event_type_key(row.event_type, row.event_sub_type)

        # timer event run times should be consistent, so we base the next run time off the last run time,
        # instead of the current timestamp
        next_run = row.next_run + int(row.event_sub_type)

        # prevents timer events from getting too far behind, or having a large "catch-up" after
        # the bot has been offline for a time
        if next_run < current_timestamp:
            next_run = current_timestamp + int(row.event_sub_type)

        with self.db.transaction():
            self.db.exec("UPDATE timer_event SET next_run = ? WHERE event_type = ? AND handler = ?",
                         [next_run, row.event_type, row.handler])

        self.call_handler(row.handler, event_type_key, None)

    def update_event_status(self, event_base_type, event_sub_type, event_handler, enabled_status):
        # clear cache
        self.db_cache[event_base_type + ":" + event_sub_type] = None

        return self.db.exec("UPDATE event_config SET enabled = ? WHERE is_hidden = 0 AND event_type = ? AND event_sub_type = ? AND handler LIKE ?",
                            [enabled_status, event_base_type, event_sub_type, event_handler])

    def get_event_types(self):
        return self.event_types

    def get_handlers(self, event_base_type, event_sub_type):
        # check first in cache
        result = self.db_cache.get(event_base_type + ":" + event_sub_type, None)
        if result is not None:
            return result
        else:
            result = self.db.query("SELECT handler FROM event_config WHERE event_type = ? AND event_sub_type = ? AND enabled = 1",
                                   [event_base_type, event_sub_type])

            # store result in cache
            self.db_cache[event_base_type + ":" + event_sub_type] = result

            return result
