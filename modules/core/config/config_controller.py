from core.decorators import instance, command
from core.db import DB
from core.text import Text
from core.chat_blob import ChatBlob
from core.command_param_types import Const, Any, Options


@instance()
class ConfigController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.command_service = registry.get_instance("command_service")
        self.event_service = registry.get_instance("event_service")
        self.setting_service = registry.get_instance("setting_service")

    def start(self):
        pass

    @command(command="config", params=[], access_level="superadmin",
             description="Show configuration options for the bot")
    def config_list_cmd(self, channel, sender, reply, args):
        sql = """SELECT
                module,
                SUM(CASE WHEN enabled = 1 THEN 1 ELSE 0 END) count_enabled,
                SUM(CASE WHEN enabled = 0 THEN 1 ELSE 0 END) count_disabled
            FROM
                (SELECT module, enabled FROM command_config
                UNION
                SELECT module, enabled FROM event_config
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
                blob += "<yellow>Partial<end>"
            elif row.count_disabled == 0:
                blob += "<green>Enabled<end>"
            else:
                blob += "<red>Disabled<end>"
            blob += "\n"

        reply(ChatBlob("Config (%d)" % count, blob))

    @command(command="config", params=[Options(["mod", "module"]), Any("module_name")], access_level="superadmin",
             description="Show configuration options for a specific module")
    def config_module_list_cmd(self, channel, sender, reply, args):
        module = args[1].lower()

        blob = ""

        data = self.db.query("SELECT name FROM setting WHERE module = ? ORDER BY name ASC", [module])
        if data:
            blob += "<header2>Settings<end>\n"
            for row in data:
                setting = self.setting_service.get(row.name)
                blob += "%s: %s (%s)\n" % (setting.get_description(), setting.get_display_value(), self.text.make_chatcmd("change", "/tell <myname> config setting " + row.name))

        data = self.db.query("SELECT DISTINCT command, sub_command FROM command_config WHERE module = ? ORDER BY command ASC", [module])
        if data:
            blob += "\n<header2>Commands<end>\n"
            for row in data:
                command_key = self.command_service.get_command_key(row.command, row.sub_command)
                blob += self.text.make_chatcmd(command_key, "/tell <myname> config cmd " + command_key) + "\n"

        data = self.db.query("SELECT event_type, event_sub_type, handler, description "
                             "FROM event_config WHERE module = ? "
                             "ORDER BY event_type, handler ASC",
                             [module])
        if data:
            blob += "\n<header2>Events<end>\n"
            for row in data:
                event_type_key = self.event_service.get_event_type_key(row.event_type, row.event_sub_type)
                blob += "%s - %s" % (self.format_event_type(row), row.description)
                blob += " " + self.text.make_chatcmd("On", "/tell <myname> config event " + event_type_key + " " + row.handler + " enable")
                blob += " " + self.text.make_chatcmd("Off", "/tell <myname> config event " + event_type_key + " " + row.handler + " disable")
                blob += "\n"

        if blob:
            reply(ChatBlob("Module (" + module + ")", blob))
        else:
            reply("Could not find module <highlight>%s<end>" % module)

    @command(command="config", params=[Const("event"), Any("event_type"), Any("event_handler"), Options(["enable", "disable"])], access_level="superadmin",
             description="Enable or disable an event")
    def config_event_status_cmd(self, channel, sender, reply, args):
        event_type = args[1].lower()
        event_handler = args[2].lower()
        action = args[3].lower()
        event_base_type, event_sub_type = self.event_service.get_event_type_parts(event_type)
        enabled = 1 if action == "enable" else 0

        if not self.event_service.is_event_type(event_base_type):
            reply("Unknown event type <highlight>%s<end>." % event_type)
            return

        count = self.event_service.update_event(event_base_type, event_sub_type, event_handler, enabled)

        if count == 0:
            reply("Could not find event for type <highlight>%s<end> and handler <highlight>%s<end>." % (event_type, event_handler))
        else:
            reply("Event type <highlight>%s<end> for handler <highlight>%s<end> has been <highlight>%sd<end> successfully." % (event_type, event_handler, action))

    @command(command="config", params=[Const("setting"), Any("setting_name"), Options(["set", "clear"]), Any("new_value", is_optional=True)], access_level="superadmin",
             description="Change a setting value")
    def config_setting_update_cmd(self, channel, sender, reply, args):
        setting_name = args[1].lower()
        op = args[2]
        new_value = args[3]

        if op == "clear":
            new_value = ""
        elif not new_value:
            reply("Error! New value required to update setting.")
            return

        setting = self.setting_service.get(setting_name)

        if setting:
            try:
                setting.set_value(new_value)
                if op == "clear":
                    reply("Setting <highlight>%s<end> has been cleared." % setting_name)
                else:
                    reply("Setting <highlight>%s<end> has been set to %s." % (setting_name, setting.get_display_value()))
            except Exception as e:
                reply("Error! %s" % str(e))
        else:
            reply("Could not find setting <highlight>%s<end>." % setting_name)

    @command(command="config", params=[Const("setting"), Any("setting_name")], access_level="superadmin",
             description="Show configuration options for a setting")
    def config_setting_show_cmd(self, channel, sender, reply, args):
        setting_name = args[1].lower()

        blob = ""

        setting = self.setting_service.get(setting_name)

        if setting:
            blob += "Current Value: <highlight>%s<end>\n" % str(setting.get_display_value())
            blob += "Description: <highlight>%s<end>\n\n" % setting.get_description()
            blob += setting.get_display()
            reply(ChatBlob("Setting (%s)" % setting_name, blob))
        else:
            reply("Could not find setting <highlight>%s<end>." % setting_name)

    def format_event_type(self, row):
        if row.event_sub_type:
            return row.event_type + ":" + row.event_sub_type
        else:
            return row.event_type
