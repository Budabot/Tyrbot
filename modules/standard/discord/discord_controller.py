from core.decorators import instance, command, event, timerevent
from core.logger import Logger
from core.setting_types import HiddenSettingType, BooleanSettingType, TextSettingType, NumberSettingType, ColorSettingType
from core.command_param_types import Int, Options, Any
from core.chat_blob import ChatBlob
from core.text import Text
from core.alts.alts_manager import AltsManager
from core.lookup.character_manager import CharacterManager
from discord import Member, ChannelType
from html.parser import HTMLParser
from .discord_wrapper import DiscordWrapper
from .discord_channel import DiscordChannel
from .discord_message import DiscordMessage
import discord
import threading
import datetime

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

@instance()
class DiscordController:
    def __init__(self):
        self.servers = []
        self.channels = {}
        self.ignore = []
        self.dthread = None
        self.dqueue = []
        self.aoqueue = []
        self.logger = Logger("discord")
        self.client = DiscordWrapper(self.channels, self.servers, self.dqueue, self.aoqueue)

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.settings_manager = registry.get_instance("setting_manager")
        self.event_manager = registry.get_instance("event_manager")
        self.online_controller = registry.get_instance("online_controller")
        self.character_manager: CharacterManager = registry.get_instance("character_manager")
        self.text: Text = registry.get_instance("text")
        self.client.register(registry)

    def pre_start(self):
        self.event_manager.register_event_type("discord_ready")
        self.event_manager.register_event_type("discord_message")
        self.event_manager.register_event_type("discord_channels")
        self.event_manager.register_event_type("discord_command")
        self.event_manager.register_event_type("discord_invites")
        self.event_manager.register_event_type("discord_exception")

        channels = self.db.query("SELECT * FROM discord")

        if channels is not None:
            for row in channels:
                a = True if row.relay_ao == 1 else False
                d = True if row.relay_dc == 1 else False
                self.channels[row.c_id] = DiscordChannel(row.c_id, row.servername, row.channelname, a, d)

    def start(self):
        self.settings_manager.register("discord_secret", "", "Discord secret token", HiddenSettingType(), "modules.standard.discord")
        self.settings_manager.register("discord_relay_type", "color", "Type of message relayed to Discord", TextSettingType(options=["embed", "color", "plain"]), "modules.standard.discord")
        self.settings_manager.register("discord_embed_color", "0", "Embedded color", NumberSettingType(options=[]), "modules.standard.discord")
        self.settings_manager.register("relay_to_private", "1", "Global setting for relaying of Discord messages to the private channel", NumberSettingType(), "modules.standard.discord")
        self.settings_manager.register("relay_to_org", "1", "Global setting for relaying of Discord message to the org channel", NumberSettingType(), "modules.standard.discord")
        self.settings_manager.register("relay_from_private", "1", "Global setting for relaying of private channel messages to the subbed Discord channels", NumberSettingType(), "modules.standard.discord")
        self.settings_manager.register("relay_from_org", "1", "Global setting for relaying of org channel messages to the subbed Discord channels", NumberSettingType(), "modules.standard.discord")
        self.settings_manager.register("relay_color_prefix", "#FCA712", "Set the prefix color for relayed messages in org/private channel", ColorSettingType(), "modules.standard.discord")
        self.settings_manager.register("relay_color_name", "#808080", "Set the color of the name in the relayed message in org/private channel", ColorSettingType(), "modules.standard.discord")
        self.settings_manager.register("relay_color_message", "#00DE42", "Set the color of the content of the relayed message in org/private channel", ColorSettingType(), "modules.standard.discord")

        self.ignore.append(str(self.bot.char_id))
        ignores = self.db.query("SELECT * FROM discord_ignore")

        if ignores is not None:
            for row in ignores:
                if row.char_id not in self.ignore:
                    self.ignore.append(str(row.char_id))

        self.update_discord_ignore()

    @command(command="dconnect", params=[], access_level="moderator", description="Manually connect to Discord, if not already connected")
    def dconnect_cmd(self, channel, sender, reply, args):
        if self.client.is_logged_in:
            reply("Already connected to Discord")
        else:
            self.connect_discord_client()

    @command(command="discord", params=[], access_level="member", description="See discord info")
    def discord_cmd(self, channel, sender, reply, args):
        counter = 0
        for cid, channel in self.channels.items():
            if channel.relay_ao or channel.relay_dc:
                counter += 1

        blob = "<header2>Info<end>\n"
        blob += "Status: "
        blob += "<green>Connected<end>\n" if self.client.is_logged_in else "<red>disconnected<end>\n"
        blob += "Channels available: <highlight>%d<end>\n\n" % (counter)

        blob += "<header2>Servers<end>\n"
        if self.servers:
            for server in self.servers:
                invites = self.text.make_chatcmd("get invite", "/tell <myname> dgetinvite %s" % (server.id))
                owner = server.owner.nick if server.owner.nick is not None else "Insufficient permissions"
                blob += "%s [%s]\n" % (server.name, invites)
                blob += " | member count: %s\n" % (str(len(server.members)))
                blob += " | owner: %s\n\n" % (server.owner.nick)
        else:
            blob += "None\n\n"

        blob += "<header2>Subscribed channels<end>\n"
        for cid, channel in self.channels.items():
            if channel.relay_ao or channel.relay_dc:
                a = "<green>On<end>" if channel.relay_ao else "<red>Off<end>"
                d = "<green>On<end>" if channel.relay_dc else "<red>Off<end>"
                blob += "<highlight>%s<end> :: <highlight>%s<end>\n" % (channel.servername, channel.channelname)
                blob += " | relaying from AO [%s]\n" % (a)
                blob += " | relaying from Discord [%s]\n" % (d)

        reply(ChatBlob("Discord info", blob))

    @command(command="drelaysetup", params=[Any("changes", is_optional=True)], access_level="moderator", description="Setup relaying of channels")
    def drelaysetup_cmd(self, channel, sender, reply, args):
        logtext = "logout" if self.client.is_logged_in else "login"
        logcmdt = "dlogout" if self.client.is_logged_in else "dconnect"
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

            alink = self.text.make_chatcmd(arelay, "/tell <myname> drelaychange %s %s %s" % (channel.channelid, "ao", arelay))
            dlink = self.text.make_chatcmd(drelay, "/tell <myname> drelaychange %s %s %s" % (channel.channelid, "discord", drelay))

            blob += "<highlight>%s<end> :: <highlight>%s<end>\n" % (channel.servername, channel.channelname)
            blob += " | relaying from AO [%s] [%s]\n" % (a, alink)
            blob += " | relaying from Discord [%s] [%s]\n" % (d, dlink)

        reply(ChatBlob("Discord setup", blob))
    
    @command(command="drelaychange", params=[Any("channel id/snowflake"), Any("relay type"), Any("on/off")], access_level="moderator", description="Changes relay setting for specific channel")
    def drelaychange_cmd(self, channel, sender, reply, args):
        cid = args[0]
        relaytype = args[1]
        relay = args[2]

        channel = self.channels[cid]

        if relaytype == "ao":
            if channel is not None:
                channel.relay_ao = True if relay == "on" else False
        elif relaytype == "discord":
            if channel is not None:
                channel.relay_dc = True if relay == "on" else False
        else:
            reply("Unknown relay type")
            return

        reply("Changed relay for %s to %s" % (channel.channelname, relay))

        self.update_discord_channels()

    @command(command="daddignore", params=[Any("char_id")], access_level="moderator", description="Add char id to relay ignore list")
    def daddignore_cmd(self, channel, sender, reply, args):
        char_id = args[0]
        
        if char_id not in self.ignore:
            self.ignore.append(char_id)
            self.update_discord_ignore()

            reply("Added char id %s to ignore list" % (char_id))
        else:
            reply("Char id already in ignore list")

    @command(command="dremignore", params=[Any("char_id")], access_level="moderator", description="Remove char id from relay ignore list")
    def dremignore_cmd(self, channel, sender, reply, args):
        char_id = args[0]

        if char_id not in self.ignore:
            reply("Char id is not in ignore list")
        else:
            self.ignore.remove(char_id)
            reply("Removed char id from ignore list")

    @command(command="dignorelist", params=[], access_level="moderator", description="See list of ignored characters")
    def dignorelist_cmd(self, channel, sender, reply, args):
        blob = "Characters ignored: <highlight>%d<end>\n\n" % len(self.ignore)

        if len(self.ignore) > 0:
            blob += "<header2>Character list<end>\n"

            for id in self.ignore:
                remove = self.text.make_chatcmd("remove", "/tell <myname> dremignore %s" % (id))
                name = self.character_manager.resolve_char_to_name(int(id))
                blob += "<highlight>%s<end> - %s [%s]\n" % (name, id, remove)

        reply(ChatBlob("Ignore list", blob))

    @command(command="dgetinvite", params=[Any("server_id")], access_level="member", description="Get an invite for specified server")
    def dgetinvite_cmd(self, channel, sender, reply, args):
        sid = args[0]

        if self.servers:
            for server in self.servers:
                if str(server.id) == sid:
                    self.aoqueue.append(("get_invite", (sender.name, server)))
        else:
            reply("No such server")

    @event(event_type="org_message", description="Relay messages to Discord from org channel, if relaying is enabled")
    def handle_org_message_event(self, event_type, event_data):
        if self.settings_manager.get("relay_from_org").get_value() != 1:
            return

        if str(event_data.char_id) not in self.ignore:
            if event_data.message[:1] != "!":
                msgtype = self.settings_manager.get("discord_relay_type").get_value()
                msgcolor = self.settings_manager.get("discord_embed_color").get_value()
                name = self.character_manager.resolve_char_to_name(event_data.char_id)
                message = DiscordMessage(msgtype, "Org", name, self.strip_html_tags(event_data.message), False, msgcolor)
                self.aoqueue.append(("org", message))

    @event(event_type="private_channel_message", description="Relay messages to Discord from private channel, if relaying is enabled")
    def handle_private_message_event(self, event_type, event_data):
        if self.settings_manager.get("relay_from_private").get_value() != 1:
            return

        if str(event_data.char_id) not in self.ignore:
            if event_data.message[:1] != "!":
                msgtype = self.settings_manager.get("discord_relay_type").get_value()
                msgcolor = self.settings_manager.get("discord_embed_color").get_value()
                name = self.character_manager.resolve_char_to_name(event_data.char_id)
                message = DiscordMessage(msgtype, "Private", name, self.strip_html_tags(event_data.message), False, msgcolor)
                self.aoqueue.append(("priv", message))

    @timerevent(budatime="1s", description="Discord relay queue handler")
    def handle_discord_queue_event(self, event_type, event_data):
        if self.dqueue:
            dtype, message = self.dqueue.pop(0)
            self.event_manager.fire_event(dtype, message)

    @event(event_type="connect", description="Connects the Discord client automatically on startup, if a token exists")
    def handle_connect_event(self, event_type, event_data):
        self.connect_discord_client()

    @event(event_type="discord_channels", description="Updates the list of channels available for relaying")
    def handle_discord_channels_event(self, event_type, message):
        for channel in message:
            if channel.type is ChannelType.text:
                cid = channel.id
                if cid not in self.channels:
                    self.channels[cid] = DiscordChannel(cid, channel.server.name, channel.name, False, False)
                else:
                    self.channels[cid].servername = channel.server.name
                    self.channels[cid].channelname = channel.name

        self.update_discord_channels()

    @event(event_type="discord_command", description="Handles discord commands")
    def handle_discord_command_event(self, event_type, message):
        msgtype = self.settings_manager.get("discord_relay_type").get_value()
        msgcolor = self.settings_manager.get("discord_embed_color").get_value()

        if message == "online":
            message = DiscordMessage(msgtype, "Command", self.bot.char_name, self.get_online_list(), True, msgcolor)
            self.aoqueue.append(("command_reply", message))

    @event(event_type="discord_message", description="Handles relaying of discord messages")
    def handle_discord_message_event(self, event_type, message):
        if isinstance(message.author, Member):
            name = message.author.nick or message.author.name
        else:
            name = message.author.name

        chanclr = self.settings_manager.get("relay_color_prefix").get_font_color()
        nameclr = self.settings_manager.get("relay_color_name").get_font_color()
        mesgclr = self.settings_manager.get("relay_color_message").get_font_color()

        content = "<grey>[<end>%sDiscord<end><grey>][<end>%s%s<end><grey>]<end> %s%s<end><grey>:<end> %s%s<end>" % (chanclr, chanclr, message.channel.name, nameclr, name, mesgclr, message.content)

        if self.settings_manager.get("relay_to_private").get_value() == 1:
            self.bot.send_private_channel_message(content)
        if self.settings_manager.get("relay_to_org").get_value() == 1:
            self.bot.send_org_message(content)

    @event(event_type="discord_invites", description="Handles invite requests")
    def handle_discord_invite_event(self, event_type, event_data):
        sender = event_data[0]
        invites = event_data[1]

        blob = "<header2>Available invites<end>\n"

        if len(invites) > 0:
            for invite in invites:
                link = self.text.make_chatcmd("join", "/start %s" % (invite.url))
                timeleft = "Permanent" if invite.max_age == 0 else str(datetime.timedelta(seconds=invite.max_age))
                used = str(invite.uses) if invite.uses is not None else "N/A"
                useleft = str(invite.max_uses) if invite.max_uses is not None else "N/A"
                channel = " | for channel: %s\n" % (invite.channel.name) if invite.channel is not None else None

                blob += "%s [%s]\n" % (invite.server.name, link)
                blob += " | life time: %s\n" % (timeleft)
                blob += " | used: %s\n" % (used)
                blob += " | uses left: %s\n" % (useleft)
                blob += channel
                blob += "\n"
        else:
            blob += "None available, maybe the bot user does not have sufficient permissions to see invites, or no invites exists.\n\n"

        self.bot.send_private_message(sender, ChatBlob("Discord invites", blob))

    @event(event_type="discord_exception", description="Handles discord exceptions")
    def handle_discord_exception_event(self, event_type, event_data):
        self.bot.send_private_channel_message("Exception raised: %s" % (event_data))
        # TODO expand... use DiscordMessage as a general case wrapper for all info that would be needed in the different relays

    def connect_discord_client(self):
        # token = self.settings_manager.get("discord_secret").get_value()
        token = "MzM5MzU2NjU2NjE1ODE3MjE2.Dhlafg.OXqFaN8SxORbviISVQzCoGJMKbw"

        if token is not None:
            self.dthread = threading.Thread(target=self.client.run, args=(token,), daemon=True)
            self.dthread.start()
            self.client.loop.create_task(self.client.relay_message())
        else:
            self.logger.error("No token registered, can't connect Discord")

    def update_discord_channels(self):
        result = self.db.query("SELECT * FROM discord")
        worked = []

        if result is not None:
            for row in result:
                if row.c_id in self.channels:
                    channel = self.channels[row.c_id]
                    self.db.exec("UPDATE discord SET servername = ?, channelname = ?, relay_ao = ?, relay_dc = ? WHERE c_id = ?", [channel.servername, channel.channelname, channel.relay_ao, channel.relay_dc, row.c_id])
                    worked.append(row.c_id)

        for cid, channel in self.channels.items():
            if channel.channelid not in worked:
                self.db.exec("INSERT INTO discord (c_id, servername, channelname, relay_ao, relay_dc) VALUES(?,?,?,?,?)", [channel.channelid, channel.servername, channel.channelname, channel.relay_ao, channel.relay_dc])

    def update_discord_ignore(self):
        ignores = self.db.query("SELECT * FROM discord_ignore")
        skip = []

        if ignores is not None:
            for row in ignores:
                skip.append(str(row.char_id))
                if str(row.char_id) not in self.ignore:
                    self.db.exec("DELETE FROM discord_ignore WHERE char_id = ?", [row.char_id])

        for cid in self.ignore:
            if cid not in skip:
                self.db.exec("INSERT INTO discord_ignore (char_id) VALUES(?)", [cid])

    def strip_html_tags(self, html):
        s = MLStripper()
        s.feed(html)
        return s.get_data()

    def get_online_list(self):
        blob = ""
        count = 0

        online_list = self.online_controller.get_online_characters("Private")

        current_main = ""
        for row in online_list:
            if current_main != row.main:
                count += 1
                blob += "\n[%s]\n" % row.main
                current_main = row.main

            blob += " | %s (%d/%d) %s %s\n" % (row.name, row.level or 0, row.ai_level or 0, row.faction, row.profession)

        return blob

# TODO !dinvite
# TODO !online from discord
