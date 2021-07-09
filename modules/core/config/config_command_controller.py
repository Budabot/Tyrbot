from core.decorators import instance, command
from core.db import DB
from core.dict_object import DictObject
from core.text import Text
from core.chat_blob import ChatBlob
from core.command_param_types import Const, Any, Options, NamedFlagParameters
from core.translation_service import TranslationService


@instance()
class ConfigCommandController:
    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.access_service = registry.get_instance("access_service")
        self.command_service = registry.get_instance("command_service")
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.ts: TranslationService = registry.get_instance("translation_service")
        self.getresp = self.ts.get_response

    @command(command="config", params=[Const("cmd"), Any("cmd_name"), Options(["enable", "disable"]), Any("channel")], access_level="admin",
             description="Enable or disable a command")
    def config_cmd_status_cmd(self, request, _, cmd_name, action, cmd_channel):
        cmd_name = cmd_name.lower()
        action = action.lower()
        cmd_channel = cmd_channel.lower()
        command_str, sub_command_str = self.command_service.get_command_key_parts(cmd_name)
        enabled = 1 if action == "enable" else 0

        if cmd_channel != "all" and not self.command_service.is_command_channel(cmd_channel):
            return self.getresp("module/config", "cmd_unknown_channel", {"channel": cmd_channel})

        if not self.has_sufficient_access_level(request.sender.char_id, command_str, sub_command_str, cmd_channel):
            return "You do not have the required access level to change this command."

        sql = "UPDATE command_config SET enabled = ? WHERE command = ? AND sub_command = ?"
        params = [enabled, command_str, sub_command_str]
        if cmd_channel != "all":
            sql += " AND channel = ?"
            params.append(cmd_channel)

        count = self.db.exec(sql, params)
        if count == 0:
            return self.getresp("module/config", "cmd_unknown_for_channel", {"channel": cmd_channel, "cmd": cmd_name})
        else:
            action = self.getresp("module/config", "enabled_low" if action == "enable" else "disabled_low")
            if cmd_channel == "all":
                return self.getresp("module/config", "cmd_toggle_success", {"cmd": cmd_name, "changedto": action})
            else:
                return self.getresp("module/config", "cmd_toggle_channel_success",
                                    {"channel": cmd_channel, "cmd": cmd_name, "changedto": action})

    @command(command="config", params=[Const("cmd"), Any("cmd_name"), Const("access_level"), Any("channel"), Any("access_level")], access_level="admin",
             description="Change access_level for a command")
    def config_cmd_access_level_cmd(self, request, _1, cmd_name, _2, cmd_channel, access_level):
        cmd_name = cmd_name.lower()
        cmd_channel = cmd_channel.lower()
        access_level = access_level.lower()
        command_str, sub_command_str = self.command_service.get_command_key_parts(cmd_name)

        if cmd_channel != "all" and not self.command_service.is_command_channel(cmd_channel):
            return self.getresp("module/config", "cmd_unknown_channel", {"channel": cmd_channel})

        if self.access_service.get_access_level_by_label(access_level) is None:
            return self.getresp("module/config", "unknown_accesslevel", {"al": access_level})

        if not self.has_sufficient_access_level(request.sender.char_id, command_str, sub_command_str, cmd_channel):
            return "You do not have the required access level to change this command."

        sql = "UPDATE command_config SET access_level = ? WHERE command = ? AND sub_command = ?"
        params = [access_level, command_str, sub_command_str]
        if cmd_channel != "all":
            sql += " AND channel = ?"
            params.append(cmd_channel)

        count = self.db.exec(sql, params)
        if count == 0:
            return self.getresp("module/config", "cmd_unknown_for_channel", {"channel": cmd_channel, "cmd": cmd_name})
        else:
            if cmd_channel == "all":
                return self.getresp("module/config", "set_accesslevel_success", {"cmd": cmd_name, "al": access_level})
            else:
                return self.getresp("module/config", "set_accesslevel_fail",
                                    {"channel": cmd_channel, "cmd": cmd_name, "al": access_level})

    @command(command="config", params=[Const("cmd"), Any("cmd_name"), NamedFlagParameters(["show_channels"])], access_level="admin",
             description="Show command configuration")
    def config_cmd_show_cmd(self, request, _, cmd_name, flag_params):
        cmd_name = cmd_name.lower()

        alias = self.command_alias_service.check_for_alias(cmd_name)
        if alias:
            cmd_name = alias

        command_str, sub_command_str = self.command_service.get_command_key_parts(cmd_name)

        cmd_channel_configs = self.get_command_channel_config(command_str, sub_command_str)

        if not cmd_channel_configs:
            return self.getresp("module/config", "no_cmd", {"cmd": cmd_name})

        blob = ""
        if flag_params.show_channels or not self.are_command_channel_configs_same(cmd_channel_configs):
            blob += self.format_cmd_channel_configs_separate_channels(cmd_name, cmd_channel_configs)
        else:
            blob += self.format_cmd_channel_configs_consolidated(cmd_name, cmd_channel_configs)

        sub_commands = self.get_sub_commands(command_str, sub_command_str)
        if sub_commands:
            blob += "<header2>Subcommands</header2>\n"
            for row in sub_commands:
                command_name = self.command_service.get_command_key(row.command, row.sub_command)
                blob += self.text.make_tellcmd(command_name, f"config cmd {command_name}") + "\n\n"

        # include help text
        blob += "\n\n".join(map(lambda handler: handler["help"], self.command_service.get_handlers(cmd_name)))
        return ChatBlob("Command (%s)" % cmd_name, blob)

    def get_sub_commands(self, command_str, sub_command_str):
        return self.db.query("SELECT DISTINCT command, sub_command FROM command_config WHERE command = ? AND sub_command != ?",
                             [command_str, sub_command_str])

    def get_command_channel_config(self, command_str, sub_command_str):
        result = []
        for command_channel, channel_label in self.command_service.channels.items():
            cmd_configs = self.command_service.get_command_configs(command=command_str,
                                                                   sub_command=sub_command_str,
                                                                   channel=command_channel,
                                                                   enabled=None)

            if len(cmd_configs) > 0:
                result.append(DictObject({"channel": command_channel,
                                          "channel_label": channel_label,
                                          "cmd_config": cmd_configs[0]}))

        return result

    def are_command_channel_configs_same(self, cmd_channel_configs):
        if len(cmd_channel_configs) < 2:
            return True

        access_level = cmd_channel_configs[0].cmd_config.access_level
        enabled = cmd_channel_configs[0].cmd_config.enabled
        for cmd_channel_config in cmd_channel_configs[1:]:
            if cmd_channel_config.cmd_config.access_level != access_level or cmd_channel_config.cmd_config.enabled != enabled:
                return False

        return True

    def format_cmd_channel_configs_separate_channels(self, cmd_name, cmd_channel_configs):
        blob = ""
        for obj in cmd_channel_configs:
            cmd_config = obj.cmd_config

            blob += "<header2>%s</header2> " % obj.channel_label
            blob += self.format_cmd_config(cmd_name, cmd_config.enabled, cmd_config.access_level, obj.channel)

        return blob

    def format_cmd_channel_configs_consolidated(self, cmd_name, cmd_channel_configs):
        cmd_config = cmd_channel_configs[0].cmd_config
        channel = "all"

        blob = ""
        blob += self.format_cmd_config(cmd_name, cmd_config.enabled, cmd_config.access_level, channel)
        blob += self.text.make_tellcmd("Configure command channels individually", f"config cmd {cmd_name} --show_channels")
        blob += "\n\n"

        return blob

    def format_cmd_config(self, cmd_name, enabled, access_level, channel):
        blob = ""
        status = self.getresp("module/config", "enabled_high" if enabled == 1 else "disabled_high")

        blob += "%s (%s: %s)\n" % (status, self.getresp("module/config", "access_level"), access_level.capitalize())

        # show status config
        blob += "Status:"
        enable_link = self.text.make_tellcmd(self.getresp("module/config", "enable"),
                                             "config cmd %s enable %s"
                                             % (cmd_name, channel))
        disable_link = self.text.make_tellcmd(self.getresp("module/config", "disable"),
                                              "config cmd %s disable %s"
                                              % (cmd_name, channel))

        blob += "  " + enable_link + "  " + disable_link

        # show access level config
        blob += "\n" + self.getresp("module/config", "access_level")
        for access_level in self.access_service.access_levels:
            # skip "None" access level
            if access_level["level"] == 0:
                continue

            label = access_level["label"]
            link = self.text.make_tellcmd(label.capitalize(), "config cmd %s access_level %s %s" % (cmd_name, channel, label))
            blob += "  " + link
        blob += "\n\n"

        return blob

    def has_sufficient_access_level(self, char_id, command_str, sub_command_str, channel):
        access_level = self.access_service.get_access_level(char_id)

        params = [command_str, sub_command_str]
        sql = "SELECT access_level FROM command_config WHERE command = ? AND sub_command = ?"
        if channel != "all":
            sql += " AND channel = ?"
            params.append(channel)

        data = self.db.query(sql, params)
        for row in data:
            if self.access_service.compare_access_levels(row.access_level, access_level["label"]) > 0:
                return False

        return True
