from core.decorators import instance, command
from core.db import DB
from core.text import Text
from core.chat_blob import ChatBlob
from core.command_param_types import Const, Any, Options, NamedFlagParameters


@instance()
class ConfigController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.util = registry.get_instance("util")
        self.command_service = registry.get_instance("command_service")
        self.event_service = registry.get_instance("event_service")
        self.setting_service = registry.get_instance("setting_service")
        self.config_events_controller = registry.get_instance("config_events_controller")

    @command(command="config", params=[], access_level="admin",
             description="Show configuration options for the bot")
    def config_list_cmd(self, request):
        sql = """SELECT
                module,
                SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) count_enabled,
                SUM(CASE WHEN enabled = 0 THEN 1 ELSE 0 END) count_disabled
            FROM
                (SELECT module, enabled FROM command_config
                UNION
                SELECT module, enabled FROM event_config WHERE is_hidden = 0
                UNION
                SELECT module, 2 FROM setting) t
            GROUP BY
                module
            ORDER BY
                module ASC"""

        data = self.db.query(sql)
        count = len(data)
        blob = ""
        current_group = ""
        for row in data:
            parts = row.module.split(".")
            group = parts[0]
            module = parts[1]
            if group != current_group:
                current_group = group
                blob += "\n<header2>" + current_group + "</header2>\n"

            blob += self.text.make_tellcmd(module, "config mod " + row.module) + " "
            if row.count_enabled > 0 and row.count_disabled > 0:
                blob += "Partial"
            else:
                blob += "<green>Enabled</green>" if row.count_disabled == 0 else "<red>Disabled</red>"
            blob += "\n"

        return ChatBlob(f"Config ({count})", blob)

    @command(command="config", params=[Options(["mod", "module"]), Any("module_name"), NamedFlagParameters(["include_hidden_events"])], access_level="admin",
             description="Show configuration options for a specific module")
    def config_module_list_cmd(self, request, _, module, named_params):
        module = module.lower()

        blob = ""

        data = self.db.query("SELECT name FROM setting WHERE module = ? ORDER BY name ASC", [module])
        if data:
            blob += "<header2>Settings</header2>\n"
            groups = self.util.group_by(data, lambda x: x.name.split("_")[0])
            for group, settings in groups.items():
                for row in settings:
                    setting = self.setting_service.get(row.name)
                    blob += "%s - %s: %s (%s)\n" % (setting.name, setting.get_description(), setting.get_display_value(), self.text.make_tellcmd("change", "config setting " + row.name))
                blob += "\n"

        data = self.db.query("SELECT DISTINCT command, sub_command FROM command_config WHERE module = ? ORDER BY command ASC", [module])
        if data:
            blob += "<header2>Commands</header2>\n"
            for row in data:
                command_key = self.command_service.get_command_key(row.command, row.sub_command)
                blob += self.text.make_tellcmd(command_key, "config cmd " + command_key) + "\n"

        blob += self.format_events(self.get_events(module, False), "Events")

        if named_params.include_hidden_events:
            blob += self.format_events(self.get_events(module, True), "Hidden Events")

        if blob:
            if not named_params.include_hidden_events:
                blob += "\n" + self.text.make_tellcmd("Include hidden events", f"config mod {module} --include_hidden_events")

            return ChatBlob(f"Module ({module})", blob)
        else:
            return "Could not find module <highlight>{module}</highlight>."

    @command(command="config", params=[Const("settinglist")], access_level="admin",
             description="List all settings")
    def config_settinglist_cmd(self, request, _):
        blob = ""

        data = self.db.query("SELECT * FROM setting ORDER BY module, name ASC")
        count = len(data)
        if data:
            blob += "<header2>Settings</header2>\n"
            current_module = ""
            for row in data:
                if row.module != current_module:
                    current_module = row.module
                    blob += "\n<pagebreak><header2>%s</header2>\n" % row.module

                setting = self.setting_service.get(row.name)
                blob += "%s - %s: %s (%s)\n" % (
                    setting.name,
                    setting.get_description(),
                    setting.get_display_value(),
                    self.text.make_tellcmd("change", "config setting " + row.name)
                )

        return ChatBlob(f"Settings ({count})", blob)

    @command(command="config", params=[Const("setting"), Any("setting_name"), Options(["set", "clear"]), Any("new_value", is_optional=True)], access_level="admin",
             description="Change a setting value")
    def config_setting_update_cmd(self, request, _, setting_name, op, new_value):
        setting_name = setting_name.lower()

        if op == "clear":
            new_value = ""
        elif not new_value:
            return "Error! New value required to update setting."

        setting = self.setting_service.get(setting_name)

        if setting:
            setting.set_value(new_value)
            if op == "clear":
                return f"Setting <highlight>{setting_name}</highlight> has been cleared."
            else:
                return f"Setting <highlight>{setting_name}</highlight> has been set to {setting.get_display_value()}."
        else:
            return f"Could not find setting <highlight>{setting_name}</highlight>."

    @command(command="config", params=[Const("setting"), Any("setting_name")], access_level="admin",
             description="Show configuration options for a setting")
    def config_setting_show_cmd(self, request, _, setting_name):
        setting_name = setting_name.lower()

        blob = ""

        setting = self.setting_service.get(setting_name)

        if setting:
            blob += f"Current Value: <highlight>{str(setting.get_display_value())}</highlight>\n"
            blob += f"Description: <highlight>{setting.get_description()}</highlight>\n\n"
            if setting.get_extended_description():
                blob += setting.get_extended_description() + "\n\n"
            blob += setting.get_display()
            return ChatBlob(f"Setting ({setting_name})", blob)
        else:
            return f"Could not find setting <highlight>{setting_name}</highlight>."

    def get_events(self, module, is_hidden):
        return self.db.query("SELECT event_type, event_sub_type, handler, description, enabled, is_hidden "
                             f"FROM event_config WHERE module = ? AND is_hidden = ? "
                             "ORDER BY is_hidden, event_type, handler ASC",
                             [module, 1 if is_hidden else 0])

    def format_events(self, data, title):
        blob = ""
        if data:
            blob += f"\n<header2>{title}</header2>\n"
            for row in data:
                event_type_key = self.event_service.get_event_type_key(row.event_type, row.event_sub_type)
                enabled = "<green>Enabled</green>" if row.enabled == 1 else "<red>Disabled</red>"
                blob += "%s - %s [%s]" % (self.config_events_controller.format_event_type(row), row.description, enabled)
                blob += " " + self.text.make_tellcmd("On", "config event %s %s enable" % (event_type_key, row.handler))
                blob += " " + self.text.make_tellcmd("Off", "config event %s %s disable" % (event_type_key, row.handler))
                if row.event_type == "timer":
                    blob += " " + self.text.make_tellcmd("Run Now", "config event %s %s run" % (event_type_key, row.handler))
                blob += "\n"
        return blob
