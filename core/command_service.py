from core.command_request import CommandRequest
from core.conn import Conn
from core.decorators import instance
from core.access_service import AccessService
from core.aochat import server_packets
from core.dict_object import DictObject
from core.feature_flags import FeatureFlags
from core.lookup.character_service import CharacterService
from core.sender_obj import SenderObj
from core.setting_service import SettingService
from core.registry import Registry
from core.logger import Logger
from core.chat_blob import ChatBlob
from core.functions import flatmap, get_attrs
import collections
import re
import inspect


@instance()
class CommandService:
    PRIVATE_MESSAGE_CHANNEL = "msg"

    def __init__(self):
        self.handlers = collections.defaultdict(list)
        self.logger = Logger(__name__)
        self.channels = {}
        self.pre_processors = []
        self.ignore_regexes = [
            re.compile(r" is AFK \(Away from keyboard\) since ", re.IGNORECASE),
            re.compile(r"I am away from my keyboard right now", re.IGNORECASE),
            re.compile(r"Unknown command or access denied!", re.IGNORECASE),
            re.compile(r"I am responding", re.IGNORECASE),
            re.compile(r"I only listen", re.IGNORECASE),
            re.compile(r"Error!", re.IGNORECASE),
            re.compile(r"Unknown command input", re.IGNORECASE),
            re.compile(r"You have been auto invited", re.IGNORECASE),
            re.compile(r"^<font")
        ]

    def inject(self, registry):
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.access_service: AccessService = registry.get_instance("access_service")
        self.bot = registry.get_instance("bot")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.event_service = registry.get_instance("event_service")
        self.setting_service: SettingService = registry.get_instance("setting_service")
        self.command_alias_service = registry.get_instance("command_alias_service")
        self.usage_service = registry.get_instance("usage_service")
        self.public_channel_service = registry.get_instance("public_channel_service")
        self.ban_service = registry.get_instance("ban_service")

    def pre_start(self):
        self.bot.register_packet_handler(server_packets.PrivateMessage.id, self.handle_private_message)

        self.register_command_channel("Private Message", self.PRIVATE_MESSAGE_CHANNEL)

    def start(self):
        access_levels = {}

        # process decorators
        for _, inst in Registry.get_all_instances().items():
            for name, method in get_attrs(inst).items():
                if hasattr(method, "command"):
                    cmd_name, params, access_level, description, help_file, sub_command, extended_description = getattr(method, "command")
                    handler = getattr(inst, name)
                    help_text = self.get_help_file(inst.module_name, help_file)

                    command_key = self.get_command_key(cmd_name.lower(), sub_command.lower() if sub_command else "")
                    al = access_levels.get(command_key, None)
                    if al is not None and al != access_level.lower():
                        raise Exception("Different access levels specified for forms of command '%s'" % command_key)
                    access_levels[command_key] = access_level

                    self.register(handler, cmd_name, params, access_level, description, inst.module_name, help_text, sub_command, extended_description)

    def register(self, handler, command, params, access_level, description, module, help_text=None, sub_command=None, extended_description=None, check_access=None):
        """
        Call during pre_start

        Args:
            handler: (request, param1, param2, ...) -> str|ChatBlob|None
            command: str
            params: [CommandParam...]
            access_level: str
            description: str
            module: str
            help_text: str
            sub_command: str
            extended_description: str
            check_access: (char_id, access_level_label) -> bool
        """

        if len(inspect.signature(handler).parameters) != len(params) + 1:
            raise Exception("Incorrect number of arguments for handler '%s.%s()'" % (handler.__module__, handler.__qualname__))

        command = command.lower()
        if sub_command:
            sub_command = sub_command.lower()
        else:
            sub_command = ""
        access_level = access_level.lower()
        module = module.lower()
        command_key = self.get_command_key(command, sub_command)

        if help_text is None:
            help_text = self.generate_help(command, description, params, extended_description)

        if check_access is None:
            check_access = self.access_service.check_access

        if not self.access_service.get_access_level_by_label(access_level):
            self.logger.error("Could not add command '%s': could not find access level '%s'" % (command, access_level))
            return

        for channel, label in self.channels.items():
            row = self.db.query_single("SELECT access_level, module, enabled, verified "
                                       "FROM command_config "
                                       "WHERE command = ? AND sub_command = ? AND channel = ?",
                                       [command, sub_command, channel])

            if row is None:
                # add new command
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
        r = re.compile(self.get_regex_from_params(params), re.IGNORECASE | re.DOTALL)
        self.handlers[command_key].append({"regex": r, "callback": handler, "help": help_text, "description": description, "params": params, "check_access": check_access})

    def register_command_pre_processor(self, pre_processor):
        """
        Call during start

        Args:
            pre_processor: (context) -> bool
        """

        self.pre_processors.append(pre_processor)

    def register_command_channel(self, label, value):
        """
        Call during pre_start

        Args:
            label: str
            value: str
        """

        if value in self.channels:
            self.logger.error("Could not register command channel '%s': command channel already registered" % value)
            return

        self.logger.debug("Registering command channel '%s'" % value)
        self.channels[value] = label

    def is_command_channel(self, channel):
        return channel in self.channels

    def process_command(self, message: str, channel: str, char_id, reply, conn):
        try:
            context = DictObject({"message": message, "char_id": char_id, "channel": channel, "reply": reply})
            for pre_processor in self.pre_processors:
                if pre_processor(context) is False:
                    return

            for regex in self.ignore_regexes:
                if regex.search(message):
                    return

            # message = html.unescape(message)

            command_str, command_args = self.get_command_parts(message)

            # check for command alias
            command_alias_str = self.command_alias_service.get_alias_command_str(command_str, command_args)

            alias_depth_count = 0
            while command_alias_str:
                alias_depth_count += 1
                command_str, command_args = self.get_command_parts(command_alias_str)
                command_alias_str = self.command_alias_service.get_alias_command_str(command_str, command_args)

                if alias_depth_count > 20:
                    raise Exception("Command alias infinite recursion detected for command '%s'" % message)

            cmd_configs = self.get_command_configs(command_str, channel, 1)
            access_level = self.access_service.get_access_level(char_id)
            sender = SenderObj(char_id, self.character_service.resolve_char_to_name(char_id, "Unknown(%d)" % char_id), access_level)
            if cmd_configs:
                # given a list of cmd_configs that are enabled, see if one has regex that matches incoming command_str
                cmd_config, matches, handler = self.get_matches(cmd_configs, command_args)
                if matches:
                    if handler["check_access"](char_id, cmd_config.access_level):
                        response = handler["callback"](CommandRequest(conn, channel, sender, reply), *self.process_matches(matches, handler["params"]))
                        if response is not None:
                            reply(response)

                        # record command usage
                        self.usage_service.add_usage(command_str, self.util.get_handler_name(handler["callback"]), char_id, channel)
                    else:
                        self.access_denied_response(message, sender, cmd_config, reply)
                else:
                    # handlers were found, but no handler regex matched
                    data = self.db.query("SELECT command, sub_command, access_level FROM command_config "
                                         "WHERE command = ? AND channel = ? AND enabled = 1",
                                         [command_str, channel])

                    help_text = self.format_help_text(data, char_id)
                    if help_text:
                        reply(self.format_help_text_blob(command_str, help_text))
                    else:
                        # the command is known, but no help is returned, therefore character does not have access to command
                        reply("Access denied.")
            else:
                self.handle_unknown_command(command_str, command_args, channel, sender, reply)
        except Exception as e:
            self.logger.error("error processing command: %s" % message, e)
            reply("There was an error processing your request.")

    def handle_unknown_command(self, command_str, command_args, channel, sender, reply):
        reply(f"Error! Unknown command <highlight>{command_str}</highlight>.")

    def access_denied_response(self, message, sender, cmd_config, reply):
        reply("Access denied.")

    def get_command_parts(self, message):
        parts = message.split(" ", 1)
        if len(parts) == 2:
            return parts[0].lower(), " " + parts[1]
        else:
            return parts[0].lower(), ""

    def get_command_configs(self, command, channel=None, enabled=1, sub_command=None):
        sql = "SELECT command, sub_command, access_level, channel, enabled FROM command_config WHERE command = ?"
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
                matches = handler["regex"].search(command_args)
                if matches:
                    return row, matches, handler
        return None, None, None

    def process_matches(self, matches, params):
        groups = list(matches.groups())

        processed = []
        for param in params:
            processed.append(param.process_matches(groups))
        return processed

    def format_help_text(self, data, char_id, show_regex=False):
        # filter out commands that character does not have access level for
        data = filter(lambda row: self.access_service.check_access(char_id, row.access_level), data)

        def get_regex(params):
            if show_regex:
                return "\n" + self.get_regex_from_params(params)
            else:
                return ""

        def read_help_text(row):
            command_key = self.get_command_key(row.command, row.sub_command)
            return filter(lambda x: x is not None, map(lambda handler: handler["help"] + get_regex(handler["params"]), self.handlers[command_key]))

        content = "\n\n".join(flatmap(read_help_text, data))
        return content if content else None

    def format_help_text_blob(self, topic, help_text):
        return ChatBlob("Help (" + topic + ")", help_text)

    def get_help_file(self, module, help_file):
        if help_file:
            try:
                help_file = "./" + module.replace(".", "/") + "/" + help_file
                with open(help_file, mode="r", encoding="UTF-8") as f:
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
        return "^" + "".join(map(lambda x: x.get_regex(), params)) + "$"

    def generate_help(self, command, description, params, extended_description=None):
        help_text = description + ":\n" + "<tab><symbol>" + command + " " + " ".join(map(lambda x: x.get_name(), params))
        if extended_description:
            help_text += "\n" + extended_description

        return help_text

    def get_handlers(self, command_key):
        return self.handlers.get(command_key, None)

    def handle_private_message(self, conn: Conn, packet: server_packets.PrivateMessage):
        if not self.setting_service.get("accept_commands_from_slave_bots").get_value() and not conn.is_main:
            return

        # since the command symbol is not required for private messages,
        # the command_str must have length of at least 1 in order to be valid,
        # otherwise it is ignored
        if len(packet.message) < 1:
            return

        # ignore leading space
        message = packet.message.lstrip()

        def reply(msg):
            if self.bot.mass_message_queue and FeatureFlags.FORCE_LARGE_MESSAGES_FROM_SLAVES and \
                    isinstance(msg, ChatBlob) and len(msg.msg) > FeatureFlags.FORCE_LARGE_MESSAGES_FROM_SLAVES_THRESHOLD:
                self.bot.send_mass_message(packet.char_id, msg, conn=conn)
            else:
                self.bot.send_private_message(packet.char_id, msg, conn=conn)

        self.process_command(
            self.trim_command_symbol(message),
            self.PRIVATE_MESSAGE_CHANNEL,
            packet.char_id,
            reply,
            conn)

    def trim_command_symbol(self, s):
        symbol = self.setting_service.get("symbol").get_value()
        if s.startswith(symbol):
            s = s[len(symbol):]
        return s
