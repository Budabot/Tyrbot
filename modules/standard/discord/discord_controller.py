import datetime
import logging
import re
import threading
from html.parser import HTMLParser

import hjson
from discord import Member, ChannelType

from core.chat_blob import ChatBlob
from core.command_param_types import Int, Any, Const, Options
from core.decorators import instance, command, event, timerevent, setting
from core.dict_object import DictObject
from core.logger import Logger
from core.lookup.character_service import CharacterService
from core.setting_types import HiddenSettingType, ColorSettingType
from core.text import Text
from core.translation_service import TranslationService
from .discord_channel import DiscordChannel
from .discord_message import DiscordMessage
from .discord_wrapper import DiscordWrapper


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
    RELAY_HUB_SOURCE = "discord"

    def __init__(self):
        self.servers = []
        self.channels = {}
        self.dthread = None
        self.dqueue = []
        self.aoqueue = []
        self.logger = Logger(__name__)
        self.client = None
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
        self.ban_service = registry.get_instance("ban_service")
        self.relay_hub_service = registry.get_instance("relay_hub_service")
        self.pork_service = registry.get_instance("pork_service")
        self.ts: TranslationService = registry.get_instance("translation_service")
        self.getresp = self.ts.get_response

    def pre_start(self):
        self.event_service.register_event_type("discord_ready")
        self.event_service.register_event_type("discord_message")
        self.event_service.register_event_type("discord_channels")
        self.event_service.register_event_type("discord_command")
        self.event_service.register_event_type("discord_invites")

    def start(self):
        self.relay_hub_service.register_relay(self.RELAY_HUB_SOURCE, self.handle_incoming_relay_message)
        self.register_discord_command_handler(self.help_discord_cmd, "help", [])

        self.db.exec("CREATE TABLE IF NOT EXISTS discord (channel_id VARCHAR(64) NOT NULL, server_name VARCHAR(256) NOT NULL, channel_name VARCHAR(256) NOT NULL, relay_ao SMALLINT NOT NULL DEFAULT 0, relay_dc SMALLINT NOT NULL DEFAULT 0)")

        channels = self.db.query("SELECT * FROM discord")

        if channels is not None:
            for row in channels:
                a = True if row.relay_ao == 1 else False
                d = True if row.relay_dc == 1 else False
                self.channels[row.channel_id] = DiscordChannel(row.channel_id, row.server_name, row.channel_name, a, d)
        self.ts.register_translation("module/discord", self.load_discord_msg)

    def load_discord_msg(self):
        with open("modules/standard/discord/discord.msg", mode="r", encoding="utf-8") as f:
            return hjson.load(f)

    @setting(name="discord_bot_token", value="", description="Discord bot token")
    def discord_bot_token(self):
        return HiddenSettingType()

    @setting(name="discord_embed_color", value="#00FF00", description="Discord embedded message color")
    def discord_embed_color(self):
        return ColorSettingType()

    @setting(name="relay_color_prefix", value="#FCA712", description="Set the prefix color for relayed messages in org/private channel")
    def relay_color_prefix(self):
        return ColorSettingType()

    @setting(name="relay_color_name", value="#808080", description="Set the color of the name in the relayed message in org/private channel")
    def relay_color_name(self):
        return ColorSettingType()

    @setting(name="relay_color_message", value="#00DE42", description="Set the color of the content of the relayed message in org/private channel")
    def relay_color_message(self):
        return ColorSettingType()

    @command(command="discord", params=[], access_level="member",
             description="See Discord info")
    def discord_cmd(self, request):
        counter = 0
        for cid, channel in self.channels.items():
            if channel.relay_ao or channel.relay_dc:
                counter += 1
        servers = ""
        if self.servers:
            for server in self.servers:
                invites = self.text.make_chatcmd(self.getresp("module/discord", "get_invite"),
                                                 "/tell <myname> discord getinvite %s" % server.id)

                owner = server.owner.nick or re.sub(pattern=r"#\d+", repl="", string=str(server.owner))
                servers += self.getresp("module/discord", "server", {"server_name": server.name,
                                                                     "invite": invites,
                                                                     "m_count": str(len(server.members)),
                                                                     "owner": owner})
        else:
            servers += self.getresp("module/discord", "no_server")

        subs = ""
        for cid, channel in self.channels.items():
            if channel.relay_ao or channel.relay_dc:
                a = self.getresp("module/discord", "on")if channel.relay_ao else self.getresp("module/discord", "off")
                d = self.getresp("module/discord", "on") if channel.relay_dc else self.getresp("module/discord", "off")
                subs += self.getresp("module/discord", "sub", {"server_name": channel.server_name,
                                                               "channel_name": channel.channel_name,
                                                               "relay_ao": a,
                                                               "relay_dc": d})
        status = self.getresp("module/discord", "connected" if self.is_connected() else "disconnected")
        blob = self.getresp("module/discord", "blob", {"connected": status,
                                                       "count": counter,
                                                       "servers": servers,
                                                       "subs": subs})

        return ChatBlob(self.getresp("module/discord", "title"), blob)

    @command(command="discord", params=[Const("connect")], access_level="moderator", sub_command="manage",
             description="Manually connect to Discord")
    def discord_connect_cmd(self, request, _):
        if self.is_connected():
            return self.getresp("module/discord", "already_connected")
        else:
            token = self.get_discord_token()
            if token:
                self.connect_discord_client(token)
                return self.getresp("module/discord", "connect_success")
            else:
                return self.getresp("module/discord", "no_token")

    @command(command="discord", params=[Const("disconnect")], access_level="moderator", sub_command="manage",
             description="Manually disconnect from Discord")
    def discord_disconnect_cmd(self, request, _):
        if not self.is_connected():
            return self.getresp("module/discord", "not_connected")
        else:
            self.disconnect_discord_client()
            return self.getresp("module/discord", "disconnect_msg")

    @command(command="discord", params=[Const("relay")], access_level="moderator", sub_command="manage",
             description="Setup relaying of channels")
    def discord_relay_cmd(self, request, _):
        action = "disconnect" if self.is_connected() else "connect"
        loglink = self.text.make_chatcmd(self.getresp("module/discord", action), "/tell <myname> discord %s" % action)
        constatus = self.getresp("module/discord", "connected" if self.is_connected() else "disconnected")
        subs = ""
        for cid, channel in self.channels.items():
            a = "<green>on<end>" if channel.relay_ao else "<red>off<end>"
            d = "<green>on<end>" if channel.relay_dc else "<red>off<end>"
            arelay = "off" if channel.relay_ao else "on"
            drelay = "off" if channel.relay_dc else "on"

            alink = self.text.make_chatcmd(self.getresp("module/discord", arelay), "/tell <myname> discord relay %s %s %s" % (channel.channel_id, "ao", arelay))
            dlink = self.text.make_chatcmd(self.getresp("module/discord", drelay), "/tell <myname> discord relay %s %s %s" % (channel.channel_id, "discord", drelay))
            subs += self.getresp("module/discord", "relay", {"server_name": channel.server_name,
                                                             "channel_name": channel.channel_name,
                                                             "relay_ao": a,
                                                             "switch_ao": alink,
                                                             "relay_dc": d,
                                                             "switch_dc": dlink
                                                             })
        blob = self.getresp("module/discord", "blob_relay", {"connected": constatus,
                                                             "switch_connection": loglink,
                                                             "count": len(self.channels),
                                                             "subs": subs})

        return ChatBlob(self.getresp("module/discord", "relay_title"), blob)

    @command(command="discord", params=[Const("relay"), Any("channel_id"), Options(["ao", "discord"]), Options(["on", "off"])], access_level="moderator",
             description="Changes relay setting for specific channel", sub_command="manage")
    def discord_relay_change_cmd(self, request, _, channel_id, relay_type, relay):
        channel = self.channels[channel_id]

        if relay_type.lower() == "ao":
            if channel is not None:
                channel.relay_ao = True if relay == "on" else False
        elif relay_type.lower() == "discord":
            if channel is not None:
                channel.relay_dc = True if relay == "on" else False
        else:

            return self.getresp("module/discord", "unknown_relay_type")

        self.update_discord_channels()
        return self.getresp("module/discord", "changed_relay", {"channel": channel.channel_name,
                                                                "changed": self.getresp("module/discord", relay)})

    @command(command="discord", params=[Const("getinvite"), Int("server_id")], access_level="member",
             description="Get an invite for specified server", sub_command="getinvite")
    def discord_getinvite_cmd(self, request, _, server_id):
        if self.servers:
            for server in self.servers:
                if server.id == str(server_id):
                    self.send_to_discord("get_invite", (request.sender.name, server))
                    return
        return self.getresp("module/discord", "no_dc", {"id": server_id})

    @timerevent(budatime="1s", description="Discord relay queue handler", is_hidden=False)
    def handle_discord_queue_event(self, event_type, event_data):
        if self.dqueue:
            dtype, message = self.dqueue.pop(0)
            self.event_service.fire_event(dtype, message)

    @event(event_type="connect", description="Connects the Discord client automatically on startup, if a token exists")
    def handle_connect_event(self, event_type, event_data):
        token = self.setting_service.get("discord_bot_token").get_value()
        if token:
            self.connect_discord_client(token)

    @event(event_type="discord_channels", description="Updates the list of channels available for relaying", is_hidden=True)
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

    @event(event_type="discord_command", description="Handles Discord commands", is_hidden=True)
    def handle_discord_command_event(self, event_type, message):
        msgcolor = self.setting_service.get("discord_embed_color").get_int_value()

        command_str, command_args = self.command_service.get_command_parts(message)
        for handler in self.command_handlers:
            if handler.command == command_str:
                matches = handler.regex.search(command_args)

                def reply(content, title="Command"):
                    self.send_to_discord("command_reply", DiscordMessage("embed", title, self.bot.char_name, self.strip_html_tags(content), msgcolor))

                ctx = DictObject()

                if matches:
                    handler.callback(ctx, reply, self.command_service.process_matches(matches, handler.params))
                else:
                    reply(self.generate_help(command_str, handler.params), "Command Help")
                break

    def generate_help(self, command_str, params):
        return "!" + command_str + " " + " ".join(map(lambda x: x.get_name(), params))

    @event(event_type="discord_message", description="Relays Discord messages to relay hub", is_hidden=True)
    def handle_discord_message_event(self, event_type, message):
        if isinstance(message.author, Member):
            name = message.author.nick or message.author.name
        else:
            name = message.author.name

        chanclr = self.setting_service.get("relay_color_prefix").get_font_color()
        nameclr = self.setting_service.get("relay_color_name").get_font_color()
        mesgclr = self.setting_service.get("relay_color_message").get_font_color()

        content = "<grey>[<end>%sDiscord<end><grey>]<end> %s%s<end><grey>:<end> %s%s<end>" % (chanclr, nameclr, name, mesgclr, message.content)

        self.relay_hub_service.send_message(self.RELAY_HUB_SOURCE, DictObject({"name": name}), content)

    @event(event_type="discord_invites", description="Handles invite requests")
    def handle_discord_invite_event(self, event_type, event_data):
        sender = event_data[0]
        invites = event_data[1]

        blob = ""
        server_invites = ""
        if len(invites) > 0:
            for invite in invites:
                link = self.text.make_chatcmd(self.getresp("module/discord", "join"), "/start %s" % invite.url)
                timeleft = "Permanent" if invite.max_age == 0 else str(datetime.timedelta(seconds=invite.max_age))
                used = str(invite.uses) if invite.uses is not None else "N/A"
                useleft = str(invite.max_uses) if invite.max_uses is not None else "N/A"
                channel = self.getresp("module/discord", "inv_channel", {"channel": invite.channel.name})\
                    if invite.channel is not None else None
                server_invites += self.getresp("module/discord", "invite", {"server": invite.server.name,
                                                                            "link": link,
                                                                            "time_left": timeleft,
                                                                            "count_used": used,
                                                                            "count_left": useleft,
                                                                            "channel": channel})
            blob += self.getresp("module/discord", "blob_invites", {"invites": server_invites})

        else:
            blob += self.getresp("module/discord", "no_invites")

        self.bot.send_private_message(sender, ChatBlob(self.getresp("module/discord", "invite_title"), blob))

    def register_discord_command_handler(self, callback, command_str, params):
        r = re.compile(self.command_service.get_regex_from_params(params), re.IGNORECASE | re.DOTALL)
        self.command_handlers.append(DictObject({"callback": callback, "command": command_str, "params": params, "regex": r}))

    def connect_discord_client(self, token):
        self.client = DiscordWrapper(self.channels, self.servers, self.dqueue, self.aoqueue, self.db)

        self.dthread = threading.Thread(target=self.run_discord_thread, args=(token,), daemon=True)
        self.dthread.start()
        self.client.loop.create_task(self.client.relay_message())

    def run_discord_thread(self, *args, **kwargs):
        should_run = True
        while should_run:
            try:
                self.client.run(*args, **kwargs)
                should_run = False
            except Exception as e:
                self.logger.error("discord connection lost", e)
                self.logger.info("reconnecting to discord")

    def disconnect_discord_client(self):
        self.client.loop.create_task(self.client.logout())
        self.client = None

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
        return self.is_connected() and char_id != self.bot.char_id and not self.ban_service.get_ban(char_id)

    def help_discord_cmd(self, ctx, reply, args):
        msg = ""
        for handler in self.command_handlers:
            msg += self.generate_help(handler.command, handler.params) + "\n"

        reply(msg, "Help")

    def is_connected(self):
        return self.client and self.client.is_logged_in

    def get_char_info_display(self, char_id):
        char_info = self.pork_service.get_character_info(char_id)
        if char_info:
            name = self.strip_html_tags(self.text.format_char_info(char_info))
        else:
            name = self.character_service.resolve_char_to_name(char_id)

        return name

    def get_discord_token(self):
        # TODO allow setting discord token in config
        token = self.setting_service.get("discord_bot_token").get_value()

        return token

    def send_to_discord(self, message_type, data):
        self.aoqueue.append((message_type, data))

    def handle_incoming_relay_message(self, ctx):
        if not self.is_connected():
            return

        message = DiscordMessage("plain", "", "", self.strip_html_tags(ctx.message))
        self.send_to_discord("msg", message)
