import time

from core.decorators import instance, command
from core.db import DB
from core.text import Text
from core.chat_blob import ChatBlob
from core.command_param_types import Const, Any, Options
from core.translation_service import TranslationService


@instance()
class ConfigEventsController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.command_service = registry.get_instance("command_service")
        self.event_service = registry.get_instance("event_service")
        self.setting_service = registry.get_instance("setting_service")
        self.ts: TranslationService = registry.get_instance("translation_service")
        self.getresp = self.ts.get_response

    @command(command="config", params=[Const("event"), Any("event_type"), Any("event_handler"), Options(["enable", "disable"])], access_level="admin",
             description="Enable or disable an event")
    def config_event_status_cmd(self, request, _, event_type, event_handler, action):
        event_type = event_type.lower()
        event_handler = event_handler.lower()
        action = action.lower()
        event_base_type, event_sub_type = self.event_service.get_event_type_parts(event_type)
        enabled = 1 if action == "enable" else 0

        if not self.event_service.is_event_type(event_base_type):
            return self.getresp("module/config", "unknown event", {"type", event_type})

        count = self.event_service.update_event_status(event_base_type, event_sub_type, event_handler, enabled)

        if count == 0:
            return self.getresp("module/config", "event_enable_fail", {"type": event_type, "handler": event_handler})
        else:
            action = self.getresp("module/config", "enabled_high" if action == "enable" else "disabled_high")
            return self.getresp("module/config", "event_enable_success", {"type": event_type,
                                                                          "handler": event_handler,
                                                                          "changedto": action})

    @command(command="config", params=[Const("event"), Any("event_type"), Any("event_handler"), Const("run")], access_level="admin",
             description="Execute a timed event immediately")
    def config_event_run_cmd(self, request, _1, event_type, event_handler, _2):
        action = "run"
        event_type = event_type.lower()
        event_handler = event_handler.lower()
        event_base_type, event_sub_type = self.event_service.get_event_type_parts(event_type)

        if not self.event_service.is_event_type(event_base_type):
            return self.getresp("module/config", "unknown event", {"type", event_type})

        row = self.db.query_single("SELECT e.event_type, e.event_sub_type, e.handler, t.next_run FROM timer_event t "
                                   "JOIN event_config e ON t.event_type = e.event_type AND t.handler = e.handler "
                                   "WHERE e.event_type = ? AND e.event_sub_type = ? AND e.handler LIKE ?", [event_base_type, event_sub_type, event_handler])

        if not row:
            return self.getresp("module/config", "event_enable_fail", {"type": event_type, "handler": event_handler})
        elif row.event_type != "timer":
            return self.getresp("module/config", "event_manual")
        else:
            self.event_service.execute_timed_event(row, int(time.time()))
            action = self.getresp("module/config", "enabled_high" if action == "enable" else "disabled_high")
            return self.getresp("module/config", "event_enable_success", {"type": event_type,
                                                                          "handler": event_handler,
                                                                          "changedto": action})

    @command(command="config", params=[Const("eventlist")], access_level="admin",
             description="List all events")
    def config_eventlist_cmd(self, request, _):
        sql = "SELECT module, event_type, event_sub_type, handler, description, enabled FROM event_config WHERE is_hidden = 0"
        sql += " ORDER BY module, event_type, event_sub_type, handler"
        data = self.db.query(sql)

        blob = ""
        current_module = ""
        for row in data:
            if current_module != row.module:
                blob += "\n<pagebreak><header2>%s<end>\n" % row.module
                current_module = row.module

            event_type_key = self.format_event_type(row)

            on_link = self.text.make_chatcmd("On", "/tell <myname> config event %s %s enable" % (event_type_key, row.handler))
            off_link = self.text.make_chatcmd("Off", "/tell <myname> config event %s %s disable" % (event_type_key, row.handler))

            blob += "%s [%s] %s %s - %s\n" % (event_type_key, self.format_enabled(row.enabled), on_link, off_link, row.description)

        return ChatBlob(self.getresp("module/config", "blob_events", {"amount": len(data)}), blob)

    def format_enabled(self, enabled):
        return "<green>E<end>" if enabled else "<red>D<end>"

    def format_event_type(self, row):
        if row.event_sub_type:
            return row.event_type + ":" + row.event_sub_type
        else:
            return row.event_type
