from core.decorators import instance
from core.access_manager import AccessManager
from core.aochat import server_packets
from core.character_manager import CharacterManager
from core.config.setting_manager import SettingManager
from core.registry import Registry
from core.logger import Logger
from core.budabot import Budabot
from core.chat_blob import ChatBlob
from __init__ import flatmap
import collections
import re


@instance()
class CommandManager:
    def __init__(self):
        self.handlers = collections.defaultdict(list)
        self.logger = Logger("command_manager")
        self.channels = ["private_message", "org_message", "private_channel_message"]
        self.deferred_register = []
        self.deferred_register_command_channel = []

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.access_manager: AccessManager = registry.get_instance("access_manager")
        self.bot: Budabot = registry.get_instance("budabot")
        self.character_manager: CharacterManager = registry.get_instance("character_manager")
        self.setting_manager: SettingManager = registry.get_instance("setting_manager")
        self.command_alias_manager = registry.get_instance("command_alias_manager")

    def start(self):
        self.bot.add_packet_handler(server_packets.PrivateMessage.id, self.handle_private_message)
        self.bot.add_packet_handler(server_packets.PrivateChannelMessage.id, self.handle_private_channel_message)
        self.db.load_sql_file("./core/config/command_config.sql")
        self.db.exec("UPDATE command_config SET verified = 0")

    def post_start(self):
        # process decorators
        for _, inst in Registry.get_all_instances().items():
            for name, method in inst.__class__.__dict__.items():
                if hasattr(method, "command"):
                    cmd_name, params, access_level, description, help_file, sub_command = getattr(method, "command")
                    handler = getattr(inst, name)
                    module = self.util.get_module_name(handler)
                    regex = "^" + params + "$"
                    help_text = self.get_help_file(module, help_file, cmd_name, description, params)

                    self.register(handler, cmd_name, regex, access_level, description, module, help_text, sub_command)

        # process deferred register calls
        for args in self.deferred_register_command_channel:
            self.do_register_command_channel(**args)

        for args in self.deferred_register:
            self.do_register(**args)

        self.db.exec("DELETE FROM command_config WHERE verified = 0")

    def register(self, handler, command, regex, access_level, description, module, help_text=None, sub_command=None):
        args = locals()
        del args["self"]
        self.deferred_register.append(args)

    def do_register(self, handler, command, regex, access_level, description, module, help_text=None, sub_command=None):
        sub_command = sub_command or command
        command = command.lower()
        sub_command = sub_command.lower()
        access_level = access_level.lower()
        module = module.lower()

        if help_text is None:
            self.logger.warning("No help text specified for for command '%s'" % command)

        if not self.access_manager.get_access_level_by_label(access_level):
            self.logger.error("Could not add command '%s': could not find access level '%s'" % (command, access_level))
            return

        for channel in self.channels:
            row = self.db.query_single("SELECT access_level, module, enabled, verified "
                                       "FROM command_config "
                                       "WHERE command = ? AND sub_command = ? AND channel = ?",
                                       [command, sub_command, channel])

            if row is None:
                # add new command config
                self.db.exec(
                    "INSERT INTO command_config "
                    "(command, sub_command, access_level, channel, module, enabled, verified) "
                    "VALUES (?, ?, ?, ?, ?, 1, 1)",
                    [command, sub_command, access_level, channel, module])
            elif row.verified:
                if row.access_level != access_level:
                    self.logger.warning(
                        "access_level different for different forms of command '%s' and sub_command '%s'" %
                        (command, sub_command))
                if row.module != module:
                    self.logger.warning(
                        "module different for different forms of command '%s' and sub_command '%s'" %
                        (command, sub_command))
            else:
                # mark command as verified
                self.db.exec("UPDATE command_config SET verified = 1, module = ? "
                             "WHERE command = ? AND sub_command = ? AND channel = ?",
                             [module, command, sub_command, channel])

        # save reference to command handler
        r = re.compile(regex, re.IGNORECASE)
        self.handlers[self.get_command_key(command, sub_command)].append(
            {"regex": r, "callback": handler, "help": help_text, "description": description})

    def register_command_channel(self, channel):
        args = locals()
        del args["self"]
        self.deferred_register_command_channel.append(args)

    def do_register_command_channel(self, channel):
        if channel in self.channels:
            self.logger.error("Could not register command channel '%s': command channel already registered"
                              % channel)
            return

        self.logger.debug("Registering command channel '%s'" % channel)
        self.channels.append(channel)

    def process_command(self, message: str, channel: str, char_name, reply):
        try:
            command_str, command_args = self.get_command_parts(message)

            # check for command alias
            command_str, command_args = self.command_alias_manager.check_for_alias(command_str, command_args)

            cmd_configs = self.get_command_configs(command_str, channel)
            if cmd_configs:
                cmd_config, matches, handler = self.get_matches(cmd_configs, command_args)
                if matches:
                    if self.access_manager.check_access(char_name, cmd_config.access_level):
                        handler["callback"](message, channel, char_name, reply, matches)
                    else:
                        reply("Error! Access denied.")
                else:
                    # handlers were found, but no handler regex matched
                    help_file = self.get_help_text(char_name, command_str, channel)
                    if help_file:
                        reply(help_file)
                    else:
                        reply("Error! Invalid syntax.")
            else:
                reply("Error! Unknown command.")
        except Exception as e:
            self.logger.error("", e)
            reply("There was an error processing your request.")

    def get_command_parts(self, message):
        parts = message.split(" ", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        else:
            return parts[0], ""

    def get_command_configs(self, command, channel):
        return self.db.query("SELECT command, sub_command, access_level FROM command_config "
                             "WHERE command = ? AND channel = ? AND enabled = 1",
                             [command, channel])

    def get_matches(self, cmd_configs, command_args):
        for row in cmd_configs:
            command_key = self.get_command_key(row.command, row.sub_command)
            handlers = self.handlers[command_key]
            for handler in handlers:
                matches = handler["regex"].match(command_args)
                if matches:
                    return row, matches, handler
        return None, None, None

    def get_help_text(self, char, command_str, channel):
        data = self.db.query("SELECT command, sub_command, access_level FROM command_config "
                             "WHERE command = ? AND channel = ? AND enabled = 1",
                             [command_str, channel])

        # filter out commands that character does not have access level for
        data = filter(lambda row: self.access_manager.check_access(char, row.access_level), data)

        def read_file(row):
            command_key = self.get_command_key(row.command, row.sub_command)
            return filter(lambda x: x is not None, map(lambda handler: handler["help"], self.handlers[command_key]))

        content = "\n\n".join(flatmap(read_file, data))
        if content:
            return ChatBlob("Help (" + command_str + ")", content)
        else:
            return None

    def get_help_file(self, module, help_file, command, description, params):
        if help_file:
            try:
                help_file = "./" + module.replace(".", "/") + "/" + help_file
                with open(help_file) as f:
                    return f.read().strip()
            except FileNotFoundError as e:
                self.logger.error("Error reading help file", e)
                return ""
        else:
            return description + ":\n" + "<tab><symbol>" + command + " " + params

    def get_command_key(self, command, sub_command):
        if command == sub_command:
            return command
        else:
            return command + ":" + sub_command

    def handle_private_message(self, packet: server_packets.PrivateMessage):
        if len(packet.message) < 1:
            return

        if packet.message[:1] == self.setting_manager.get("symbol"):
            command_str = packet.message[1:]
        else:
            command_str = packet.message

        self.process_command(
            command_str,
            "private_message",
            self.character_manager.get_char_name(packet.character_id),
            lambda msg: self.bot.send_private_message(packet.character_id, msg))

    def handle_private_channel_message(self, packet: server_packets.PrivateChannelMessage):
        if len(packet.message) < 2:
            return

        symbol = packet.message[:1]
        command_str = packet.message[1:]
        if symbol == self.setting_manager.get("symbol") and packet.character_id == self.bot.char_id:
            self.process_command(
                command_str,
                "private_channel_message",
                self.character_manager.get_char_name(packet.character_id),
                lambda msg: self.bot.send_private_channel_message(msg))
