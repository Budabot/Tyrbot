from core.decorators import instance, command
from core.db import DB
from core.text import Text
from core.chat_blob import ChatBlob
from core.commands.param_types import Const, Any, Options


@instance()
class ConfigCommandController:
    def __init__(self):
        pass

    def inject(self, registry):
        self.db: DB = registry.get_instance("db")
        self.text: Text = registry.get_instance("text")
        self.access_manager = registry.get_instance("access_manager")
        self.command_manager = registry.get_instance("command_manager")

    def start(self):
        pass

    @command(command="config", params=[Const("cmd"), Any("cmd_name"), Options(["enable", "disable"]), Any("channel")],
             access_level="superadmin",
             description="Enable or disable a command")
    def config_cmd_status_cmd(self, channel, sender, reply, args):
        cmd_name = args[1].lower()
        action = args[2].lower()
        cmd_channel = args[3].lower()
        command_str, sub_command_str = self.command_manager.get_command_key_parts(cmd_name)
        enabled = 1 if action == "enable" else 0

        if cmd_channel != "all" and not self.command_manager.is_command_channel(cmd_channel):
            reply("Unknown command channel <highlight>%s<end>." % cmd_channel)
            return

        sql = "UPDATE command_config SET enabled = ? WHERE command = ? AND sub_command = ?"
        params = [enabled, command_str, sub_command_str]
        if cmd_channel != "all":
            sql += " AND channel = ?"
            params.append(cmd_channel)

        count = self.db.exec(sql, params)
        if count == 0:
            reply("Could not find command <highlight>%s<end> for channel <highlight>%s<end>." % (cmd_name, cmd_channel))
        else:
            if cmd_channel == "all":
                reply("Command <highlight>%s<end> has been <highlight>%sd<end> successfully." % (cmd_name, action))
            else:
                reply("Command <highlight>%s<end> for channel <highlight>%s<end> has been <highlight>%sd<end>"
                      " successfully." % (cmd_name, channel, action))

    @command(command="config", params=[Const("cmd"), Any("cmd_name"), Const("access_level"), Any("channel"), Any("access_level")],
             access_level="superadmin",
             description="Change access_level for a command")
    def config_cmd_access_level_cmd(self, channel, sender, reply, args):
        cmd_name = args[1].lower()
        cmd_channel = args[2].lower()
        access_level = args[3].lower()
        command_str, sub_command_str = self.command_manager.get_command_key_parts(cmd_name)

        if cmd_channel != "all" and not self.command_manager.is_command_channel(cmd_channel):
            reply("Unknown command channel <highlight>%s<end>." % cmd_channel)
            return

        if not self.access_manager.get_access_level_by_label(access_level):
            reply("Unknown access level <highlight>%s<end>." % access_level)
            return

        sql = "UPDATE command_config SET access_level = ? WHERE command = ? AND sub_command = ?"
        params = [access_level, command_str, sub_command_str]
        if cmd_channel != "all":
            sql += " AND channel = ?"
            params.append(cmd_channel)

        count = self.db.exec(sql, params)
        if count == 0:
            reply("Could not find command <highlight>%s<end> for channel <highlight>%s<end>." % (cmd_name, cmd_channel))
        else:
            if cmd_channel == "all":
                reply("Access level <highlight>%s<end> for command <highlight>%s<end> has been set successfully." %
                      (access_level, cmd_name))
            else:
                reply("Access level <highlight>%s<end> for command <highlight>%s<end> on channel <highlight>%s<end>"
                      " has been set successfully." % (access_level, cmd_name, channel))

    @command(command="config", params=[Const("cmd"), Any("cmd_name")],
             access_level="superadmin",
             description="Enable or disable a command")
    def config_cmd_show_cmd(self, channel, sender, reply, args):
        cmd_name = args[1].lower()
        command_str, sub_command_str = self.command_manager.get_command_key_parts(cmd_name)

        blob = ""
        for channel, channel_label in self.command_manager.channels.items():
            cmd_configs = self.command_manager.get_command_configs(command=command_str,
                                                                   sub_command=sub_command_str,
                                                                   channel=channel,
                                                                   enabled=None)
            if len(cmd_configs) > 0:
                cmd_config = cmd_configs[0]
                if cmd_config.enabled == 1:
                    status = "<green>Enabled<end>"
                else:
                    status = "<red>Disabled<end>"

                blob += "<header2>%s<end> %s (Access Level: %s)\n" % (channel_label, status, cmd_config.access_level.capitalize())

                blob += "Status:"
                enable_link = self.text.make_chatcmd("Enable",
                                                     "/tell <myname> config cmd %s enable %s" %
                                                     (cmd_name, channel))
                disable_link = self.text.make_chatcmd("Disable",
                                                      "/tell <myname> config cmd %s disable %s" %
                                                      (cmd_name, channel))

                blob += "  " + enable_link + "  " + disable_link

                blob += "\nAccess Level:"
                for access_level in self.access_manager.access_levels:
                    if access_level["level"] == 0:
                        continue

                    label = access_level["label"]
                    link = self.text.make_chatcmd(label.capitalize(),
                                                  "/tell <myname> config cmd %s access_level %s %s" %
                                                  (cmd_name, channel, label))
                    blob += "  " + link
                blob += "\n"
            blob += "\n"

        reply(ChatBlob("%s Command Config" % cmd_name.capitalize(), blob))
