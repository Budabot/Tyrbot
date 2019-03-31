from core.decorators import instance, command, event, timerevent, setting
from core.dict_object import DictObject
from core.logger import Logger
from core.private_channel_service import PrivateChannelService
from core.public_channel_service import PublicChannelService
from core.setting_types import HiddenSettingType, BooleanSettingType, TextSettingType, ColorSettingType
from core.command_param_types import Int, Any, Const, Options
from core.chat_blob import ChatBlob
from core.text import Text
from core.lookup.character_service import CharacterService
from discord import Member, ChannelType
from html.parser import HTMLParser
from .discord_wrapper import DiscordWrapper
from .discord_channel import DiscordChannel
from .discord_message import DiscordMessage
import threading
import datetime
import logging
import re


class MLStripper(HTMLParser):
    def error(self, message):
        pass

    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return "".join(self.fed)


@instance()
class DiscordController:
    def __init__(self):
        self.servers = []
        self.channels = {}
        self.dthread = None
        self.dqueue = []
        self.aoqueue = []
        self.logger = Logger(__name__)
        self.client = DiscordWrapper(self.channels, self.servers, self.dqueue, self.aoqueue)
        self.command_handlers = []

        logging.getLogger("discord").setLevel(logging.INFO)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.setting_service = registry.get_instance("setting_service")
        self.event_service = registry.get_instance("event_service")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.text: Text = registry.get_instance("text")
        self.command_service = registry.get_instance("command_service")
        self.client.register(registry)

    def pre_start(self):
        self.event_service.register_event_type("discord_ready")
        self.event_service.register_event_type("discord_message")
        self.event_service.register_event_type("discord_channels")
        self.event_service.register_event_type("discord_command")
        self.event_service.register_event_type("discord_invites")

        channels = self.db.query("SELECT * FROM discord")

        if channels is not None:
            for row in channels:
                a = True if row.relay_ao == 1 else False
                d = True if row.relay_dc == 1 else False
                self.channels[row.channel_id] = DiscordChannel(row.channel_id, row.server_name, row.channel_name, a, d)

    def start(self):
        self.register_discord_command_handler(self.help_discord_cmd, "help", [])

    @setting(name="discord_bot_token", value="", description="Discord bot token")
    def discord_bot_token(self):
        return HiddenSettingType()

    @setting(name="discord_embed_color", value="#00FF00", description="Discord embedded message color")
    def discord_embed_color(self):
        return ColorSettingType()

    @setting(name="relay_to_private", value="true", description="Global setting for relaying of Discord messages to the private channel")
    def relay_to_private(self):
        return BooleanSettingType()

    @setting(name="relay_to_org", value="true", description="Global setting for relaying of Discord message to the org channel")
    def relay_to_org(self):
        return BooleanSettingType()

    @setting(name="relay_color_prefix", value="#FCA712", description="Set the prefix color for relayed messages in org/private channel")
    def relay_color_prefix(self):
        return ColorSettingType()

    @setting(name="relay_color_name", value="#808080", description="Set the color of the name in the relayed message in org/private channel")
    def relay_color_name(self):
        return ColorSettingType()

    @setting(name="relay_color_message", value="#00DE42", description="Set the color of the content of the relayed message in org/private channel")
    def relay_color_message(self):
        return ColorSettingType()

    @command(command="discord", params=[Const("connect")], access_level="moderator", sub_command="manage",
             description="Manually connect to Discord")
    def discord_connect_cmd(self, request, _):
        if self.client.is_logged_in:
            return "Already connected to Discord."
        else:
            token = self.setting_service.get("discord_bot_token").get_value()
            if token:
                self.connect_discord_client(token)
                return "Connecting to discord..."
            else:
                return "Cannot connect to discord, no bot token is set."

    @command(command="discord", params=[Const("disconnect")], access_level="moderator", sub_command="manage",
             description="Manually disconnect from Discord")
    def discord_disconnect_cmd(self, request, _):
        pass

    @command(command="discord", params=[], access_level="member",
             description="See discord info")
    def discord_cmd(self, request):
        counter = 0
        for cid, channel in self.channels.items():
            if channel.relay_ao or channel.relay_dc:
                counter += 1

        blob = "<header2>Info<end>\n"
        blob += "Status: "
        blob += "<green>Connected<end>\n" if self.client.is_logged_in else "<red>disconnected<end>\n"
        blob += "Channels available: <highlight>%d<end>\n\n" % counter

        blob += "<header2>Servers<end>\n"
        if self.servers:
            for server in self.servers:
                invites = self.text.make_chatcmd("get invite", "/tell <myname> discord getinvite %s" % server.id)
                owner = server.owner.nick if server.owner.nick is not None else "Insufficient permissions"
                blob += "%s [%s]\n" % (server.name, invites)
                blob += " | member count: %s\n" % (str(len(server.members)))
                blob += " | owner: %s\n\n" % owner
        else:
            blob += "None\n\n"

        blob += "<header2>Subscribed channels<end>\n"
        for cid, channel in self.channels.items():
            if channel.relay_ao or channel.relay_dc:
                a = "<green>On<end>" if channel.relay_ao else "<red>Off<end>"
                d = "<green>On<end>" if channel.relay_dc else "<red>Off<end>"
                blob += "<highlight>%s<end> :: <highlight>%s<end>\n" % (channel.server_name, channel.channel_name)
                blob += " | relaying from AO [%s]\n" % a
                blob += " | relaying from Discord [%s]\n" % d

        blob += "\n\nDiscord Module written by <highlight>Vladimirovna<end>"

        return ChatBlob("Discord info", blob)

    @command(command="discord", params=[Const("relay")], access_level="moderator", sub_command="manage",
             description="Setup relaying of channels")
    def discord_relay_cmd(self, request, _):
        logtext = "disconnect" if self.client.is_logged_in else "connect"
        logcmdt = "discord disconnect" if self.client.is_logged_in else "discord connect"
        loglink = self.text.make_chatcmd(logtext, "/tell <myname> %s" % logcmdt)
        constatus = "<green>Connected<end>" if self.client.is_logged_in else "<red>disconnected<end>"

        blob = "<header2>Info<end>\n"
        blob += "Status: %s [%s]\n" % (constatus, loglink)
        blob += "Channels available: <highlight>%d<end>\n\n" % len(self.channels)

        blob += "<header2>Subscription setup<end>\n"
        for cid, channel in self.channels.items():
            a = "<green>on<end>" if channel.relay_ao else "<red>off<end>"
            d = "<green>on<end>" if channel.relay_dc else "<red>off<end>"

            arelay = "off" if channel.relay_ao else "on"
            drelay = "off" if channel.relay_dc else "on"

            alink = self.text.make_chatcmd(arelay, "/tell <myname> discord relay %s %s %s" % (channel.channel_id, "ao", arelay))
            dlink = self.text.make_chatcmd(drelay, "/tell <myname> discord relay %s %s %s" % (channel.channel_id, "discord", drelay))

            blob += "<highlight>%s<end> :: <highlight>%s<end>\n" % (channel.server_name, channel.channel_name)
            blob += " | relaying from AO [%s] [%s]\n" % (a, alink)
            blob += " | relaying from Discord [%s] [%s]\n" % (d, dlink)

        blob += "\n\nDiscord Module written by <highlight>Vladimirovna<end>"

        return ChatBlob("Discord Relay", blob)
    
    @command(command="discord", params=[Const("relay"), Any("channel_id"), Options(["ao", "discord"]), Options(["on", "off"])], access_level="moderator",
             description="Changes relay setting for specific channel", sub_command="manage")
    def discord_relay_change_cmd(self, request, _, channel_id, relay_type, relay):
        channel = self.channels[channel_id]

        if relay_type == "ao":
            if channel is not None:
                channel.relay_ao = True if relay == "on" else False
        elif relay_type == "discord":
            if channel is not None:
                channel.relay_dc = True if relay == "on" else False
        else:
            return "Unknown relay type."

        self.update_discord_channels()

        return "Changed relay for %s to %s." % (channel.channel_name, relay)

    @command(command="discord", params=[Const("getinvite"), Int("server_id")], access_level="moderator",
             description="Get an invite for specified server", sub_command="manage")
    def discord_getinvite_cmd(self, request, _, server_id):
        if self.servers:
            for server in self.servers:
                if server.id == str(server_id):
                    self.aoqueue.append(("get_invite", (request.sender.name, server)))
                    return
        return "No such server."

    @event(event_type=PublicChannelService.ORG_CHANNEL_MESSAGE_EVENT, description="Relay messages to Discord from org channel")
    def handle_org_message_event(self, event_type, event_data):
        if self.should_relay_message(event_data.char_id):
            if event_data.message[:1] != "!":
                msg = event_data.extended_message.get_message() if event_data.extended_message else event_data.message
                msgcolor = self.setting_service.get("discord_embed_color").get_int_value()
                name = self.character_service.resolve_char_to_name(event_data.char_id)
                message = DiscordMessage("plain", "Org", name, self.strip_html_tags(msg), False, msgcolor)
                self.aoqueue.append(("org", message))

    @event(event_type=PrivateChannelService.PRIVATE_CHANNEL_MESSAGE_EVENT, description="Relay messages to Discord from private channel")
    def handle_private_message_event(self, event_type, event_data):
        if self.should_relay_message(event_data.char_id):
            if event_data.message[:1] != "!":
                msgcolor = self.setting_service.get("discord_embed_color").get_int_value()
                name = self.character_service.resolve_char_to_name(event_data.char_id)
                message = DiscordMessage("plain", "Private", name, self.strip_html_tags(event_data.message), False, msgcolor)
                self.aoqueue.append(("priv", message))

    @timerevent(budatime="1s", description="Discord relay queue handler")
    def handle_discord_queue_event(self, event_type, event_data):
        if self.dqueue:
            dtype, message = self.dqueue.pop(0)
            self.event_service.fire_event(dtype, message)

    @event(event_type="connect", description="Connects the Discord client automatically on startup, if a token exists")
    def handle_connect_event(self, event_type, event_data):
        token = self.setting_service.get("discord_bot_token").get_value()
        if token:
            self.connect_discord_client(token)

    @event(event_type="discord_channels", description="Updates the list of channels available for relaying")
    def handle_discord_channels_event(self, event_type, message):
        for channel in message:
            if channel.type is ChannelType.text:
                cid = channel.id
                if cid not in self.channels:
                    self.channels[cid] = DiscordChannel(cid, channel.server.name, channel.name, False, False)
                else:
                    self.channels[cid].server_name = channel.server.name
                    self.channels[cid].channel_name = channel.name

        self.update_discord_channels()

    @event(event_type="discord_command", description="Handles discord commands")
    def handle_discord_command_event(self, event_type, message):
        msgcolor = self.setting_service.get("discord_embed_color").get_int_value()

        command_str, command_args = self.command_service.get_command_parts(message)
        for handler in self.command_handlers:
            if handler.command == command_str:
                matches = handler.regex.search(command_args)

                def reply(content, title="Command"):
                    self.aoqueue.append(("command_reply", DiscordMessage("embed", title, self.bot.char_name, self.strip_html_tags(content), True, msgcolor)))

                if matches:
                    handler.callback(reply, self.command_service.process_matches(matches, handler.params))
                else:
                    reply(self.generate_help(command_str, handler.params), "Command Help")
                break

    def generate_help(self, command_str, params):
        return "!" + command_str + " " + " ".join(map(lambda x: x.get_name(), params))

    @event(event_type="discord_message", description="Handles relaying of discord messages")
    def handle_discord_message_event(self, event_type, message):
        if isinstance(message.author, Member):
            name = message.author.nick or message.author.name
        else:
            name = message.author.name

        chanclr = self.setting_service.get("relay_color_prefix").get_font_color()
        nameclr = self.setting_service.get("relay_color_name").get_font_color()
        mesgclr = self.setting_service.get("relay_color_message").get_font_color()

        content = "<grey>[<end>%sDiscord<end><grey>][<end>%s%s<end><grey>]<end> %s%s<end><grey>:<end> %s%s<end>" % (chanclr, chanclr, message.channel.name, nameclr, name, mesgclr, message.content)

        if self.setting_service.get("relay_to_private").get_value():
            self.bot.send_private_channel_message(content, fire_outgoing_event=False)

        if self.setting_service.get("relay_to_org").get_value():
            self.bot.send_org_message(content, fire_outgoing_event=False)

    @event(event_type="discord_invites", description="Handles invite requests")
    def handle_discord_invite_event(self, event_type, event_data):
        sender = event_data[0]
        invites = event_data[1]

        blob = "<header2>Available invites<end>\n"

        if len(invites) > 0:
            for invite in invites:
                link = self.text.make_chatcmd("join", "/start %s" % invite.url)
                timeleft = "Permanent" if invite.max_age == 0 else str(datetime.timedelta(seconds=invite.max_age))
                used = str(invite.uses) if invite.uses is not None else "N/A"
                useleft = str(invite.max_uses) if invite.max_uses is not None else "N/A"
                channel = " | for channel: %s\n" % invite.channel.name if invite.channel is not None else None

                blob += "%s [%s]\n" % (invite.server.name, link)
                blob += " | life time: %s\n" % timeleft
                blob += " | used: %s\n" % used
                blob += " | uses left: %s\n" % useleft
                blob += channel
                blob += "\n"
        else:
            blob += "None available, maybe the bot user does not have sufficient permissions to see invites, or no invites exists.\n\n"

        self.bot.send_private_message(sender, ChatBlob("Discord invites", blob))

    def register_discord_command_handler(self, callback, command_str, params):
        r = re.compile(self.command_service.get_regex_from_params(params), re.IGNORECASE | re.DOTALL)
        self.command_handlers.append(DictObject({"callback": callback, "command": command_str, "params": params, "regex": r}))

    def connect_discord_client(self, token):
        self.dthread = threading.Thread(target=self.client.run, args=(token,), daemon=True)
        self.dthread.start()
        self.client.loop.create_task(self.client.relay_message())

    def update_discord_channels(self):
        result = self.db.query("SELECT * FROM discord")
        worked = []

        if result is not None:
            for row in result:
                if row.channel_id in self.channels:
                    channel = self.channels[row.channel_id]
                    self.db.exec("UPDATE discord SET server_name = ?, channel_name = ?, relay_ao = ?, relay_dc = ? WHERE channel_id = ?",
                                 [channel.server_name, channel.channel_name, channel.relay_ao, channel.relay_dc, row.channel_id])
                    worked.append(row.channel_id)

        for cid, channel in self.channels.items():
            if channel.channel_id not in worked:
                self.db.exec("INSERT INTO discord (channel_id, server_name, channel_name, relay_ao, relay_dc) VALUES (?, ?, ?, ?, ?)",
                             [channel.channel_id, channel.server_name, channel.channel_name, channel.relay_ao, channel.relay_dc])

    def strip_html_tags(self, html):
        s = MLStripper()
        s.feed(html)
        return s.get_data()

    def should_relay_message(self, char_id):
        return self.client.is_logged_in and char_id != self.bot.char_id

    def help_discord_cmd(self, reply, args):
        msg = ""
        for handler in self.command_handlers:
            msg += self.generate_help(handler.command, handler.params) + "\n"

        reply(msg, "Help")
