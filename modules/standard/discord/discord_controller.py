import datetime
import re
import threading
from functools import partial
from html.parser import HTMLParser

import hjson
from discord import Member, ChannelType

from core.alts.alts_service import AltsService
from core.chat_blob import ChatBlob
from core.command_param_types import Int, Const, Character
from core.decorators import instance, command, event, timerevent, setting
from core.dict_object import DictObject
from core.logger import Logger
from core.lookup.character_service import CharacterService
from core.setting_types import HiddenSettingType, ColorSettingType, TextSettingType, BooleanSettingType
from core.text import Text
from core.translation_service import TranslationService

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
        self.chat_commands = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return "".join(self.fed)

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for k, v in attrs:
                if k == "href" and v.startswith("chatcmd://"):
                    self.chat_commands.append(v[10:])
                    return
            self.chat_commands.append("")

    def handle_endtag(self, tag):
        if tag == "a":
            cmd = self.chat_commands.pop(0)
            if cmd:
                cmd = cmd.replace("/tell <myname> ", "!")
                self.handle_data(f" `{cmd}`")


@instance()
class DiscordController:
    MESSAGE_SOURCE = "discord"
    COMMAND_CHANNEL = "discord"

    def __init__(self):
        self.dthread = None
        self.dqueue = []
        self.aoqueue = []
        self.logger = Logger(__name__)
        self.client = None
        self.command_handlers = []

    def inject(self, registry):
        self.bot = registry.get_instance("bot")
        self.db = registry.get_instance("db")
        self.util = registry.get_instance("util")
        self.setting_service = registry.get_instance("setting_service")
        self.event_service = registry.get_instance("event_service")
        self.character_service: CharacterService = registry.get_instance("character_service")
        self.text: Text = registry.get_instance("text")
        self.command_service = registry.get_instance("command_service")
        self.ban_service = registry.get_instance("ban_service")
        self.message_hub_service = registry.get_instance("message_hub_service")
        self.pork_service = registry.get_instance("pork_service")
        self.alts_service = registry.get_instance("alts_service")
        self.ts: TranslationService = registry.get_instance("translation_service")
        self.getresp = self.ts.get_response

    def pre_start(self):
        self.event_service.register_event_type("discord_ready")
        self.event_service.register_event_type("discord_message")
        self.event_service.register_event_type("discord_channels")
        self.event_service.register_event_type("discord_command")
        self.event_service.register_event_type("discord_invites")

        self.message_hub_service.register_message_source(self.MESSAGE_SOURCE)

        self.command_service.register_command_channel("Discord", self.COMMAND_CHANNEL)

    def start(self):
        self.db.exec("CREATE TABLE IF NOT EXISTS discord_char_link (discord_id BIGINT NOT NULL, char_id INT NOT NULL)")

        self.message_hub_service.register_message_destination(self.MESSAGE_SOURCE,
                                                              self.handle_incoming_relay_message,
                                                              ["private_channel", "org_channel", "websocket_relay", "tell_relay", "shutdown_notice"],
                                                              [self.MESSAGE_SOURCE])

        self.register_discord_command_handler(self.discord_link_cmd, "discord", [Const("link"), Character("ao_character")])
        self.register_discord_command_handler(self.discord_unlink_cmd, "discord", [Const("unlink")])

        self.ts.register_translation("module/discord", self.load_discord_msg)

        self.setting_service.register_new(self.module_name, "discord_enabled", False, BooleanSettingType(), "Enable the Discord relay")
        self.setting_service.register_new(self.module_name, "discord_bot_token", "", HiddenSettingType(allow_empty=True), "Discord bot token")
        self.setting_service.register_new(self.module_name, "discord_channel_name", "general", TextSettingType(["general"], allow_empty=True), "Discord channel name to relay with")
        self.setting_service.register_new(self.module_name, "discord_embed_color", "#00FF00", ColorSettingType(), "Discord embedded message color")
        self.setting_service.register_new(self.module_name, "relay_color_prefix", "#FCA712", ColorSettingType(), "Set the prefix color for messages coming from Discord")
        self.setting_service.register_new(self.module_name, "relay_color_name", "#808080", ColorSettingType(), "Set the color of the name for messages coming from Discord")
        self.setting_service.register_new(self.module_name, "relay_color_message", "#00DE42", ColorSettingType(), "Set the color of the content for messages coming from Discord")

        self.setting_service.register_change_listener("discord_channel_name", self.update_discord_channel_name)
        self.setting_service.register_change_listener("discord_enabled", self.update_discord_state)

    def load_discord_msg(self):
        with open("modules/standard/discord/discord.msg", mode="r", encoding="utf-8") as f:
            return hjson.load(f)

    @command(command="discord", params=[], access_level="member",
             description="See Discord info")
    def discord_cmd(self, request):
        servers = ""
        if self.client and self.client.guilds:
            for server in self.client.guilds:
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
        for channel in self.get_text_channels():
            subs += self.getresp("module/discord", "sub", {"server_name": channel.guild.name,
                                                           "channel_name": channel.name})
        status = self.getresp("module/discord", "connected" if self.is_connected() else "disconnected")
        blob = self.getresp("module/discord", "blob", {"connected": status,
                                                       "count": len(self.get_text_channels()),
                                                       "servers": servers,
                                                       "subs": subs})

        return ChatBlob(self.getresp("module/discord", "title"), blob)

    @command(command="discord", params=[Const("relay")], access_level="moderator", sub_command="manage",
             description="Setup relaying of channels")
    def discord_relay_cmd(self, request, _):
        action = "disconnect" if self.is_connected() else "connect"
        loglink = self.text.make_chatcmd(self.getresp("module/discord", action), "/tell <myname> discord %s" % action)
        constatus = self.getresp("module/discord", "connected" if self.is_connected() else "disconnected")
        subs = ""
        for channel in self.get_text_channels():
            select_link = self.text.make_chatcmd("select", "/tell <myname> config setting discord_channel_name set %s" % channel.name)
            selected = "(selected)" if self.setting_service.get("discord_channel_name").get_value() == channel.name else ""
            subs += self.getresp("module/discord", "relay", {"server_name": channel.guild.name,
                                                             "channel_name": channel.name,
                                                             "select": select_link,
                                                             "selected": selected
                                                             })

        blob = self.getresp("module/discord", "blob_relay", {"connected": constatus,
                                                             "switch_connection": loglink,
                                                             "count": len(self.get_text_channels()),
                                                             "subs": subs})

        return ChatBlob(self.getresp("module/discord", "relay_title"), blob)

    @command(command="discord", params=[Const("confirm"), Int("discord_id")], access_level="member",
             description="Confirm link of a Discord user")
    def discord_confirm_cmd(self, request, _, discord_id):
        main = self.alts_service.get_main(request.sender.char_id)
        if main.char_id != request.sender.char_id:
            return self.getresp("module/discord", "must_run_from_main", {"char": main.name})

        self.db.exec("DELETE FROM discord_char_link WHERE discord_id = ? OR char_id = ?", [discord_id, main.char_id])
        self.db.exec("INSERT INTO discord_char_link (discord_id, char_id) VALUES (?, ?)", [discord_id, main.char_id])

        return self.getresp("module/discord", "link_success", {"discord_user": discord_id})

    @command(command="discord", params=[Const("getinvite"), Int("server_id")], access_level="member",
             description="Get an invite for specified server", sub_command="getinvite")
    def discord_getinvite_cmd(self, request, _, server_id):
        if self.client and self.client.guilds:
            for server in self.client.guilds:
                if server.id == server_id:
                    self.send_to_discord("get_invite", (request.sender.name, server))
                    return
        return self.getresp("module/discord", "no_dc", {"id": server_id})

    @timerevent(budatime="1s", description="Discord relay queue handler", is_hidden=True)
    def handle_discord_queue_event(self, event_type, event_data):
        if self.dqueue:
            dtype, message = self.dqueue.pop(0)

            if dtype == "discord_message":
                if message.channel.type == ChannelType.private or message.content.startswith(self.setting_service.get("symbol").get_value()):
                    self.handle_discord_command_event(message)
                else:
                    self.handle_discord_message_event(message)
            elif dtype == "discord_ready":
                self.send_to_discord("msg", DiscordMessage("plain", "", "", f"{self.bot.char_name} is now connected."))

            self.event_service.fire_event(dtype, message)

    @timerevent(budatime="1m", description="Ensure the bot is connected to Discord", is_enabled=False, is_hidden=True, run_at_startup=True)
    def handle_connect_event(self, event_type, event_data):
        if not self.is_connected():
            self.connect_discord_client()

    @event(event_type=AltsService.MAIN_CHANGED_EVENT_TYPE, description="Update discord character link when a main is changed", is_hidden=True)
    def handle_main_changed(self, event_type, event_data):
        old_row = self.db.query_single("SELECT discord_id FROM discord_char_link WHERE char_id = ?", [event_data.old_main_id])
        if old_row:
            new_row = self.db.query_single("SELECT discord_id FROM discord_char_link WHERE char_id = ?", [event_data.new_main_id])
            if not new_row:
                self.db.exec("INSERT INTO discord_char_link (discord_id, char_id) VALUES (?, ?)", [old_row.discord_id, event_data.new_main_id])

    @event(event_type="discord_invites", description="Handles invite requests", is_hidden=True)
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
                server_invites += self.getresp("module/discord", "invite", {"server": invite.guild.name,
                                                                            "link": link,
                                                                            "time_left": timeleft,
                                                                            "count_used": used,
                                                                            "count_left": useleft,
                                                                            "channel": channel})
            blob += self.getresp("module/discord", "blob_invites", {"invites": server_invites})

        else:
            blob += self.getresp("module/discord", "no_invites")

        self.bot.send_private_message(sender, ChatBlob(self.getresp("module/discord", "invite_title"), blob))

    def handle_discord_command_event(self, message):
        if not self.find_discord_command_handler(message):
            reply = partial(self.discord_command_reply, channel=message.channel)
            row = self.db.query_single("SELECT char_id FROM discord_char_link WHERE discord_id = ?", [message.author.id])
            if row:
                message_str = self.command_service.trim_command_symbol(message.content)
                self.command_service.process_command(message_str, self.COMMAND_CHANNEL, row.char_id, reply)
            else:
                reply(self.getresp("module/discord", "discord_user_not_linked"))

    def handle_discord_message_event(self, message):
        if isinstance(message.author, Member):
            name = message.author.nick or message.author.name
        else:
            name = message.author.name

        chanclr = self.setting_service.get("relay_color_prefix").get_font_color()
        nameclr = self.setting_service.get("relay_color_name").get_font_color()
        mesgclr = self.setting_service.get("relay_color_message").get_font_color()

        formatted_message = "<grey>[<end>%sDiscord<end><grey>]<end> %s%s<end><grey>:<end> %s%s<end>" % (chanclr, nameclr, name, mesgclr, message.content)

        self.message_hub_service.send_message(self.MESSAGE_SOURCE, DictObject({"name": name}), message.content, formatted_message)

    def find_discord_command_handler(self, message):
        message_str = self.command_service.trim_command_symbol(message.content)
        command_str, command_args = self.command_service.get_command_parts(message_str)
        for handler in self.command_handlers:
            if handler.command == command_str:
                matches = handler.regex.search(command_args)

                if matches:
                    ctx = DictObject({"message": message})

                    handler.callback(ctx, partial(self.discord_command_reply, channel=message.channel),
                                     self.command_service.process_matches(matches, handler.params))
                    return True
        return False

    def discord_command_reply(self, content, title=None, channel=None):
        if isinstance(content, ChatBlob):
            if not title:
                title = content.title

            content = content.page_prefix + content.msg + content.page_postfix

        if not title:
            title = "Command"
        title = self.format_message(title)

        if isinstance(content, str):
            msgcolor = self.setting_service.get("discord_embed_color").get_int_value()
            pages = self.text.split_by_separators(self.format_message(content), 2048) # discord max is 2048
            num_pages = len(pages)
            page_title = title
            for page_num, page in enumerate(pages, start=1):
                if num_pages > 1:
                    page_title = title + f" (Page {page_num} / {num_pages})"
                self.send_to_discord("command_reply", DiscordMessage("embed", page_title, self.bot.char_name, page, channel, msgcolor))
            return

        if isinstance(content, DiscordMessage):
            self.send_to_discord("command_reply", content)
        else:
            self.logger.error("unable to process message for discord: " + content)

    def generate_help(self, command_str, params):
        return "!" + command_str + " " + " ".join(map(lambda x: x.get_name(), params))

    def format_message(self, msg):
        msg = re.sub(r"<header>(.*?)<end>\n?", r"```less\n\1\n```", msg)
        msg = re.sub(r"<header2>(.*?)<end>\n?", r"```yaml\n\1\n```", msg)
        msg = re.sub(r"<highlight>(.*?)<end>", r"`\1`", msg)
        return self.strip_html_tags(msg)

    def register_discord_command_handler(self, callback, command_str, params):
        """Call during start"""
        r = re.compile(self.command_service.get_regex_from_params(params), re.IGNORECASE | re.DOTALL)
        self.command_handlers.append(DictObject({"callback": callback, "command": command_str, "params": params, "regex": r}))

    def connect_discord_client(self):
        token = self.setting_service.get("discord_bot_token").get_value()
        if not token:
            self.logger.warning("Unable to connect to Discord, discord_bot_token has not been set")
        else:
            self.disconnect_discord_client()

            self.client = DiscordWrapper(
                self.setting_service.get("discord_channel_name").get_value(),
                self.dqueue,
                self.aoqueue)

            self.dthread = threading.Thread(target=self.run_discord_thread, args=(self.client, token), daemon=True)
            self.dthread.start()

    def run_discord_thread(self, client, token):
        try:
            self.logger.info("connecting to discord")
            client.loop.create_task(client.start(token))
            client.loop.run_until_complete(client.relay_message())
        except Exception as e:
            self.logger.error("discord connection lost", e)

    def disconnect_discord_client(self):
        if self.client:
            self.client.loop.create_task(self.client.logout_with_message(f"{self.bot.char_name} is disconnecting..."))
            self.client = None
        if self.dthread:
            self.dthread.join()
            self.dthread = None
        self.dqueue = []
        self.aoqueue = []

    def strip_html_tags(self, html):
        s = MLStripper()
        s.feed(html)
        return s.get_data()

    def should_relay_message(self, char_id):
        return self.is_connected() and char_id != self.bot.char_id and not self.ban_service.get_ban(char_id)

    def discord_link_cmd(self, ctx, reply, args):
        char = args[1]
        if not char.char_id:
            reply(self.getresp("global", "char_not_found", {"char": char.name}))
            return

        main = self.alts_service.get_main(char.char_id)
        if main.char_id != char.char_id:
            reply(self.getresp("module/discord", "must_link_main"))
            return

        author = ctx.message.author
        discord_user = "%s#%s (%d)" % (author.name, author.discriminator, author.id)
        blob = self.getresp("module/discord", "confirm_instructions", {"discord_user": discord_user,
                                                                       "confirm_link": self.text.make_chatcmd("Confirm", "/tell <myname> discord confirm %d" % author.id)})
        self.bot.send_private_message(char.char_id, ChatBlob("Discord Confirm Link", blob))

        reply(self.getresp("module/discord", "link_response", {"char": char.name}))

    def discord_unlink_cmd(self, ctx, reply, args):
        self.db.exec("DELETE FROM discord_char_link WHERE discord_id = ?", [ctx.message.author.id])

        reply(self.getresp("module/discord", "unlink_success"))

    def is_connected(self):
        #not self.client or not self.dthread.is_alive()
        return self.client and self.client.is_ready() and self.dthread and self.dthread.is_alive()

    def get_char_info_display(self, char_id):
        char_info = self.pork_service.get_character_info(char_id)
        if char_info:
            name = self.strip_html_tags(self.text.format_char_info(char_info))
        else:
            name = self.character_service.resolve_char_to_name(char_id)

        return name

    def send_to_discord(self, message_type, data):
        self.aoqueue.append((message_type, data))

    def handle_incoming_relay_message(self, ctx):
        if not self.is_connected():
            return

        message = DiscordMessage("plain", "", "", self.strip_html_tags(ctx.formatted_message))
        self.send_to_discord("msg", message)

    def get_text_channels(self):
        if self.client:
            return self.client.get_text_channels()
        else:
            return []

    def update_discord_channel_name(self, setting_name, old_value, new_value):
        if self.client:
            if not self.client.set_channel_name(new_value):
                self.logger.warning(f"Could not find discord channel '{new_value}'")

    def update_discord_state(self, setting_name, old_value, new_value):
        if setting_name == "discord_enabled":
            event_handlers = [self.handle_connect_event, self.handle_discord_queue_event, self.handle_discord_invite_event]
            for handler in event_handlers:
                event_handler = self.util.get_handler_name(handler)
                event_base_type, event_sub_type = self.event_service.get_event_type_parts(handler.event[0])
                self.event_service.update_event_status(event_base_type, event_sub_type, event_handler, 1 if new_value else 0)

            if not new_value:
                self.disconnect_discord_client()
