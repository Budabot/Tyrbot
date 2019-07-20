import hjson

from core.decorators import instance, command
from core.db import DB
from core.text import Text
from core.chat_blob import ChatBlob
from core.command_param_types import Const, Any, Options
from core.translation_service import TranslationService


@instance()
class ConfigController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.command_service = registry.get_instance("command_service")
        self.event_service = registry.get_instance("event_service")
        self.setting_service = registry.get_instance("setting_service")
        self.config_events_controller = registry.get_instance("config_events_controller")
        self.ts: TranslationService = registry.get_instance("translation_service")
        self.getresp = self.ts.get_response

    def start(self):
        self.ts.register_translation("module/config", self.load_config_msg)

    def load_config_msg(self):
        with open("modules/core/config/config.msg", mode="r", encoding="UTF-8") as f:
            return hjson.load(f)

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
                blob += "\n<header2>" + current_group + "<end>\n"

            blob += self.text.make_chatcmd(module, "/tell <myname> config mod " + row.module) + " "
            if row.count_enabled > 0 and row.count_disabled > 0:
                blob +=self.getresp("module/config", "partial")
            else:
                blob +=self.getresp("module/config", "enabled_high" if row.count_disabled == 0 else "disabled_high")
            blob += "\n"

        return ChatBlob(self.getresp("module/config", "config", {"count": count}), blob)

    @command(command="config", params=[Options(["mod", "module"]), Any("module_name")], access_level="admin",
             description="Show configuration options for a specific module")
    def config_module_list_cmd(self, request, _, module):
        module = module.lower()

        blob = ""

        data = self.db.query("SELECT name FROM setting WHERE module = ? ORDER BY name ASC", [module])
        if data:
            blob += self.getresp("module/config", "settings")
            for row in data:
                setting = self.setting_service.get(row.name)
                blob += "%s: %s (%s)\n" % (setting.get_description(), setting.get_display_value(), self.text.make_chatcmd("change", "/tell <myname> config setting " + row.name))

        data = self.db.query("SELECT DISTINCT command, sub_command FROM command_config WHERE module = ? ORDER BY command ASC", [module])
        if data:
            blob += self.getresp("module/config", "commands")
            for row in data:
                command_key = self.command_service.get_command_key(row.command, row.sub_command)
                blob += self.text.make_chatcmd(command_key, "/tell <myname> config cmd " + command_key) + "\n"

        data = self.db.query("SELECT event_type, event_sub_type, handler, description, enabled "
                             "FROM event_config WHERE module = ? AND is_hidden = 0 "
                             "ORDER BY event_type, handler ASC",
                             [module])
        if data:
            blob += self.getresp("module/config", "events")
            for row in data:
                event_type_key = self.event_service.get_event_type_key(row.event_type, row.event_sub_type)
                enabled = self.getresp("module/config", "enabled_high" if row.enabled == 1 else "disabled_high")
                blob += "%s - %s [%s]" % (self.config_events_controller.format_event_type(row), row.description, enabled)
                blob += " " + self.text.make_chatcmd("On", "/tell <myname> config event %s %s enable" % (event_type_key, row.handler))
                blob += " " + self.text.make_chatcmd("Off", "/tell <myname> config event %s %s disable" % (event_type_key, row.handler))
                if row.event_type == 'timer':
                    blob += " " + self.text.make_chatcmd("Run Now", "/tell <myname> config event %s %s run" % (event_type_key, row.handler))
                blob += "\n"

        if blob:
            return ChatBlob(self.getresp("module/config", "mod_title", {"mod": module}), blob)
        else:
            return self.getresp("module/config", "mod_not_found", {"mod": module})

    @command(command="config", params=[Const("setting"), Any("setting_name"), Options(["set", "clear"]), Any("new_value", is_optional=True)], access_level="admin",
             description="Change a setting value")
    def config_setting_update_cmd(self, request, _, setting_name, op, new_value):
        setting_name = setting_name.lower()

        if op == "clear":
            new_value = ""
        elif not new_value:
            return self.getresp("module/config", "no_new_value")
        setting = self.setting_service.get(setting_name)

        if setting:
            try:
                setting.set_value(new_value)
                if op == "clear":
                    return self.getresp("module/config", "set_clr", {"setting": setting_name})
                else:
                    return self.getresp("module/config", "set_new", {"setting": setting_name,
                                                                     "value": setting.get_display_value()})
            except Exception as e:
                return "Error! %s" % str(e)
        else:
            return self.getresp("module/config", "setting_not_found", {"setting": setting_name})

    @command(command="config", params=[Const("setting"), Any("setting_name")], access_level="admin",
             description="Show configuration options for a setting")
    def config_setting_show_cmd(self, request, _, setting_name):
        setting_name = setting_name.lower()

        blob = ""

        setting = self.setting_service.get(setting_name)

        if setting:
            blob += self.getresp("module/config", "current_value", {"value": str(setting.get_display_value())})
            blob += self.getresp("module/config", "description", {"desc": setting.get_description()})
            blob += setting.get_display()
            return ChatBlob(self.getresp("module/config", "setting", {"setting": setting_name}), blob)
        else:
            return self.getresp("module/config", "setting_not_found", {"setting": setting_name})
