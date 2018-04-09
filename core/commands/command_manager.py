from core.decorators import instance
from core.access_manager import AccessManager
from core.aochat import server_packets
from core.character_manager import CharacterManager
from core.settings.setting_manager import SettingManager
from core.registry import Registry
from core.logger import Logger
from core.budabot import Budabot
from core.chat_blob import ChatBlob
from core.map_object import MapObject
from __init__ import flatmap
import collections
import re
import os


@instance()
class CommandManager:
    def __init__(self):
        self.handlers = collections.defaultdict(list)
        self.logger = Logger("command_manager")
        self.channels = {}
        self.deferred_register = []

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
        self.db.load_sql_file("command_config.sql", os.path.dirname(__file__))
        self.db.exec("UPDATE command_config SET verified = 0")
        self.register_command_channel("Private Message", "msg")
        self.register_command_channel("Org Channel", "org")
        self.register_command_channel("Private Channel", "priv")

    # taken from: https://stackoverflow.com/a/8529229/280574 and modified
    def get_attrs(self, obj):
        attrs = {}
        for cls in obj.__class__.__mro__:
            attrs.update(cls.__dict__.items())
        attrs.update(obj.__class__.__dict__.items())
        return attrs

    def post_start(self):
        # process decorators
        for _, inst in Registry.get_all_instances().items():
            for name, method in self.get_attrs(inst).items():
                if hasattr(method, "command"):
                    cmd_name, params, access_level, description, help_file, sub_command = getattr(method, "command")
                    handler = getattr(inst, name)
                    module = self.util.get_module_name(handler)
                    help_text = self.get_help_file(module, help_file)
                    self.register(handler, cmd_name, params, access_level, description, module, help_text, sub_command)

        # process deferred register calls
        for args in self.deferred_register:
            self.do_register(**args)

        self.db.exec("DELETE FROM command_config WHERE verified = 0")

    def register(self, handler, command, params, access_level, description, module, help_text=None, sub_command=None):
        args = locals()
        del args["self"]
        self.deferred_register.append(args)

    def do_register(self, handler, command, params, access_level, description, module, help_text=None, sub_command=None):
        command = command.lower()
        if sub_command:
            sub_command = sub_command.lower()
        else:
            sub_command = ""
        access_level = access_level.lower()
        module = module.lower()
        command_key = self.get_command_key(command, sub_command)

        if help_text is None:
            help_text = self.generate_help(command, description, params)

        if not self.access_manager.get_access_level_by_label(access_level):
            self.logger.error("Could not add command '%s': could not find access level '%s'" % (command, access_level))
            return

        for channel, label in self.channels.items():
            row = self.db.query_single("SELECT access_level, module, enabled, verified "
                                       "FROM command_config "
                                       "WHERE command = ? AND sub_command = ? AND channel = ?",
                                       [command, sub_command, channel])

            if row is None:
                # add new command commands
                self.db.exec(
                    "INSERT INTO command_config "
                    "(command, sub_command, access_level, channel, module, enabled, verified) "
                    "VALUES (?, ?, ?, ?, ?, 1, 1)",
                    [command, sub_command, access_level, channel, module])
            elif row.verified:
                if row.module != module:
                    self.logger.warning("module different for different forms of command '%s' and sub_command '%s'" % (command, sub_command))
            else:
                # mark command as verified
                self.db.exec("UPDATE command_config SET verified = 1, module = ? "
                             "WHERE command = ? AND sub_command = ? AND channel = ?",
                             [module, command, sub_command, channel])

        # save reference to command handler
        r = re.compile(self.get_regex_from_params(params), re.IGNORECASE)
        self.handlers[command_key].append({"regex": r, "callback": handler, "help": help_text, "description": description})

    def register_command_channel(self, label, value):
        if value in self.channels:
            self.logger.error("Could not register command channel '%s': command channel already registered" % value)
            return

        self.logger.debug("Registering command channel '%s'" % value)
        self.channels[value] = label

    def is_command_channel(self, channel):
        return channel in self.channels

    def process_command(self, message: str, channel: str, char_id, reply):
        try:
            command_str, command_args = self.get_command_parts(message)

            # check for command alias
            command_str, command_args = self.command_alias_manager.check_for_alias(command_str, command_args)

            cmd_configs = self.get_command_configs(command_str, channel, 1)
            if cmd_configs:
                # given a list of cmd_configs that are enabled, see if one has regex that matches incoming command_str
                cmd_config, matches, handler = self.get_matches(cmd_configs, command_args)
                if matches:
                    if self.access_manager.check_access(char_id, cmd_config.access_level):
                        sender = MapObject({"name": self.character_manager.resolve_char_to_name(char_id), "char_id": char_id})
                        handler["callback"](channel, sender, reply, matches)
                    else:
                        self.access_denied_response(char_id, cmd_config, reply)
                else:
                    # handlers were found, but no handler regex matched
                    help_text = self.get_help_text(char_id, command_str, channel)
                    if help_text:
                        reply(self.format_help_text(command_str, help_text))
                    else:
                        reply("Error! Invalid syntax.")
            else:
                reply("Error! Unknown command.")
        except Exception as e:
            self.logger.error("", e)
            reply("There was an error processing your request.")

    def access_denied_response(self, char_id, cmd_config, reply):
        reply("Error! Access denied.")

    def get_command_parts(self, message):
        parts = message.split(" ", 1)
        if len(parts) == 2:
            return parts[0].lower(), parts[1]
        else:
            return parts[0].lower(), ""

    def get_command_configs(self, command, channel=None, enabled=1, sub_command=None):
        sql = "SELECT command, sub_command, access_level, enabled FROM command_config WHERE command = ?"
        params = [command]
        if channel:
            sql += " AND channel = ?"
            params.append(channel)
        if enabled:
            sql += " AND enabled = ?"
            params.append(enabled)
        if sub_command:
            sql += " AND sub_command = ?"
            params.append(sub_command)

        sql += " ORDER BY sub_command, channel"

        return self.db.query(sql, params)

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

        def read_help_text(row):
            command_key = self.get_command_key(row.command, row.sub_command)
            return filter(lambda x: x is not None, map(lambda handler: handler["help"], self.handlers[command_key]))

        content = "\n\n".join(flatmap(read_help_text, data))
        return content if content else None

    def format_help_text(self, topic, help_text):
        return ChatBlob("Help (" + topic + ")", help_text)

    def get_help_file(self, module, help_file):
        if help_file:
            try:
                help_file = "./" + module.replace(".", "/") + "/" + help_file
                with open(help_file) as f:
                    return f.read().strip()
            except FileNotFoundError as e:
                self.logger.error("Error reading help file", e)
        return None

    def get_command_key(self, command, sub_command):
        if sub_command:
            return command + ":" + sub_command
        else:
            return command

    def get_command_key_parts(self, command_str):
        parts = command_str.split(":", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        else:
            return parts[0], ""

    def get_regex_from_params(self, params):
        # params must be wrapped with line-beginning and line-ending anchors in order to match
        # when no params are specified (eg. "^$")
        return "^" + " ".join(map(lambda x: x.get_regex(), params)) + "$"

    def generate_help(self, command, description, params):
        return description + ":\n" + "<tab><symbol>" + command + " " + " ".join(map(lambda x: x.get_name(), params))

    def get_handlers(self, command_key):
        return self.handlers.get(command_key, None)

    def handle_private_message(self, packet: server_packets.PrivateMessage):
        # since the command symbol is not required for private messages,
        # the command_str must have length of at least 1 in order to be valid,
        # otherwise it is ignored
        if len(packet.message) < 1:
            return

        if packet.message[:1] == self.setting_manager.get("symbol").get_value():
            command_str = packet.message[1:]
        else:
            command_str = packet.message

        self.process_command(
            command_str,
            "msg",
            packet.character_id,
            lambda msg: self.bot.send_private_message(packet.character_id, msg))

    def handle_private_channel_message(self, packet: server_packets.PrivateChannelMessage):
        # since the command symbol is required in the private channel,
        # the command_str must have length of at least 2 in order to be valid,
        # otherwise it is ignored
        if len(packet.message) < 2:
            return

        symbol = packet.message[:1]
        command_str = packet.message[1:]
        if symbol == self.setting_manager.get("symbol").get_value() and packet.private_channel_id == self.bot.char_id:
            self.process_command(
                command_str,
                "priv",
                packet.character_id,
                lambda msg: self.bot.send_private_channel_message(msg))
