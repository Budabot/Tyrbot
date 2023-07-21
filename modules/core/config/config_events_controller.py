import time

from core.decorators import instance, command
from core.db import DB
from core.text import Text
from core.chat_blob import ChatBlob
from core.command_param_types import Const, Any, Options, NamedParameters


@instance()
class ConfigEventsController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.command_service = registry.get_instance("command_service")
        self.event_service = registry.get_instance("event_service")
        self.setting_service = registry.get_instance("setting_service")

    @command(command="config", params=[Const("event"), Any("event_type"), Any("event_handler"), Options(["enable", "disable"])], access_level="admin",
             description="Enable or disable an event")
    def config_event_status_cmd(self, request, _, event_type, event_handler, action):
        event_type = event_type.lower()
        event_handler = event_handler.lower()
        action = action.lower()
        event_base_type, event_sub_type = self.event_service.get_event_type_parts(event_type)
        enabled = 1 if action == "enable" else 0

        if not self.event_service.is_event_type(event_base_type):
            return f"Unknown event type <highlight>{event_type}</highlight>."

        count = self.event_service.update_event_status(event_base_type, event_sub_type, event_handler, enabled)

        if count == 0:
            return f"Could not find event for type <highlight>{event_type}</highlight> and handler <highlight>{event_handler}</highlight>."
        else:
            action_str = "<green>Enabled</green>" if action == "enable" else "<red>Disabled</red>"
            return f"Event type <highlight>{event_type}</highlight> for handler <highlight>{event_handler}</highlight> has been {action_str} successfully."

    @command(command="config", params=[Const("event"), Any("event_type"), Any("event_handler"), Const("run")], access_level="admin",
             description="Execute a timed event immediately")
    def config_event_run_cmd(self, request, _1, event_type, event_handler, _2):
        action = "run"
        event_type = event_type.lower()
        event_handler = event_handler.lower()
        event_base_type, event_sub_type = self.event_service.get_event_type_parts(event_type)

        if not self.event_service.is_event_type(event_base_type):
            return f"Unknown event type <highlight>{event_type}</highlight>."

        row = self.db.query_single("SELECT e.event_type, e.event_sub_type, e.handler, t.next_run FROM timer_event t "
                                   "JOIN event_config e ON t.event_type = e.event_type AND t.handler = e.handler "
                                   "WHERE e.event_type = ? AND e.event_sub_type = ? AND e.handler LIKE ?", [event_base_type, event_sub_type, event_handler])

        if not row:
            return f"Could not find event for type <highlight>{event_type}</highlight> and handler <highlight>{event_handler}</highlight>."
        elif row.event_type != "timer":
            return "Only <highlight>timer</highlight> events can be run manually."
        else:
            self.event_service.execute_timed_event(row, int(time.time()))
            return f"Event type <highlight>{event_type}</highlight> for handler <highlight>{event_handler}</highlight> has been run successfully."

    @command(command="config", params=[Const("event"), NamedParameters(["event_type"])], access_level="admin",
             description="List all events")
    def config_eventlist_cmd(self, request, _, named_params):
        params = []
        sql = "SELECT module, event_type, event_sub_type, handler, description, enabled, is_hidden FROM event_config"
        #sql += " WHERE is_hidden = 0"
        if named_params.event_type:
            sql += " WHERE event_type = ?"
            params.append(named_params.event_type)
        sql += " ORDER BY module, is_hidden, event_type, event_sub_type, handler"
        data = self.db.query(sql, params)

        blob = "Asterisk (*) denotes a hidden event. Only change these events if you understand the implications.\n"
        current_module = ""
        for row in data:
            if current_module != row.module:
                blob += "\n<pagebreak><header2>%s</header2>\n" % row.module
                current_module = row.module

            event_type_key = self.format_event_type(row)

            on_link = self.text.make_tellcmd("On", "config event %s %s enable" % (event_type_key, row.handler))
            off_link = self.text.make_tellcmd("Off", "config event %s %s disable" % (event_type_key, row.handler))

            if row.is_hidden == 1:
                blob += "*"
            blob += "%s [%s] %s %s - %s\n" % (event_type_key, self.format_enabled(row.enabled), on_link, off_link, row.description)

        return ChatBlob(f"Events ({len(data)})", blob)

    def format_enabled(self, enabled):
        return "<green>E</green>" if enabled else "<red>D</red>"

    def format_event_type(self, row):
        if row.event_sub_type:
            return row.event_type + ":" + row.event_sub_type
        else:
            return row.event_type
