import re
import threading
import time
from datetime import timezone
from functools import partial
from html.parser import HTMLParser

from discord import Member, ChannelType

from core.alts_service import AltsService
from core.chat_blob import ChatBlob
from core.command_param_types import Int, Const, Character
from core.decorators import instance, command, event, timerevent
from core.dict_object import DictObject
from core.logger import Logger
from core.lookup.character_service import CharacterService
from core.setting_types import HiddenSettingType, ColorSettingType, TextSettingType, BooleanSettingType
from core.standard_message import StandardMessage
from core.text import Text

from .discord_message import DiscordEmbedMessage, DiscordTextMessage, DiscordMessage
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
                                                              ["private_channel", "org_channel", "websocket_relay", "shutdown_notice"],
                                                              [self.MESSAGE_SOURCE])

        self.register_discord_command_handler(self.discord_link_cmd, "discord", [Const("link"), Character("ao_character")])
        self.register_discord_command_handler(self.discord_unlink_cmd, "discord", [Const("unlink")])

        self.setting_service.register(self.module_name, "discord_enabled", False, BooleanSettingType(), "Enable the Discord relay")
        self.setting_service.register(self.module_name, "discord_bot_token", "", HiddenSettingType(allow_empty=True), "Discord bot token")
        self.setting_service.register(self.module_name, "discord_channel_id", "", TextSettingType(allow_empty=True),
                                      "Discord channel id for relaying messages to and from",
                                      "You can get the Discord channel ID by right-clicking on a channel name in Discord and then clicking \"Copy ID\"")
        self.setting_service.register(self.module_name, "discord_embed_color", "#00FF00", ColorSettingType(), "Discord embedded message color")
        self.setting_service.register(self.module_name, "relay_color_prefix", "#FCA712", ColorSettingType(), "Set the prefix color for messages coming from Discord")
        self.setting_service.register(self.module_name, "relay_color_name", "#808080", ColorSettingType(), "Set the color of the name for messages coming from Discord")
        self.setting_service.register(self.module_name, "relay_color_message", "#00DE42", ColorSettingType(), "Set the color of the content for messages coming from Discord")

        self.setting_service.register_change_listener("discord_channel_id", self.update_discord_channel)
        self.setting_service.register_change_listener("discord_enabled", self.update_discord_state)

    @command(command="discord", params=[], access_level="member",
             description="See Discord info")
    def discord_cmd(self, request):
        status = "<green>Connected</green>" if self.is_connected() else "<red>Disconnected</red>"

        blob = "<header2>Info</header2>\n"
        blob += f"Status: {status}\n"
        blob += f"Channels available: <highlight>{len(self.get_text_channels())}</highlight>\n\n"
        blob += "<header2>Servers</header2>\n"

        if self.client and self.client.guilds:
            for server in self.client.guilds:
                invites = self.text.make_tellcmd("Get invite", "discord getinvite %s" % server.id)
                owner = server.owner.nick or re.sub(pattern=r"#\d+", repl="", string=str(server.owner))
                blob += f"{server.name} [{invites}]\n"
                blob += f" └ member count: {len(server.members)}\n"
                blob += f" └ owner: {owner}\n\n"
        else:
            blob += "None\n\n"

        blob += "<header2>Channels</header2>\n"
        for channel in self.get_text_channels():
            blob += f"<highlight>{channel.guild.name}</highlight> :: <highlight>{channel.name}</highlight>\n"

        blob += "\n\nDiscord Module written by <highlight>Vladimirovna</highlight>\n"

        return ChatBlob("Discord Info", blob)

    @command(command="discord", params=[Const("relay")], access_level="moderator", sub_command="manage",
             description="Setup relaying of channels")
    def discord_relay_cmd(self, request, _):
        connect_link = self.text.make_tellcmd("<green>Connect</green>", "config setting discord_enabled set true")
        disconnect_link = self.text.make_tellcmd("<red>Disconnect</red>", "config setting discord_enabled set false")
        constatus = "<green>Connected</green>" if self.is_connected() else "<red>Disconnected</red>"

        blob = "<header2>Info</header2>\n"
        blob += f"Status: {constatus} [{connect_link} {disconnect_link}]\n"
        blob += f"Channels available: <highlight>{len(self.get_text_channels())}</highlight>\n\n"
        blob += "<header2>Subscription setup</header2>\n"
        for channel in self.get_text_channels():
            select_link = self.text.make_tellcmd("select", "config setting discord_channel_id set %s" % channel.id)
            selected = "(selected)" if self.setting_service.get("discord_channel_id").get_value() == channel.id else ""
            blob += f"<highlight>{channel.guild.name}</highlight> :: <highlight>{channel.name}</highlight> [{select_link}] {selected}\n"

        blob += "\n\nDiscord Module written by <highlight>Vladimirovna</highlight>\n"

        return ChatBlob("Discord Relay", blob)

    @command(command="discord", params=[Const("confirm"), Int("discord_id")], access_level="member",
             description="Confirm link of a Discord user")
    def discord_confirm_cmd(self, request, _, discord_id):
        main = self.alts_service.get_main(request.sender.char_id)
        if main.char_id != request.sender.char_id:
            return "You must run this command from your main character."

        self.db.exec("DELETE FROM discord_char_link WHERE discord_id = ? OR char_id = ?", [discord_id, main.char_id])
        self.db.exec("INSERT INTO discord_char_link (discord_id, char_id) VALUES (?, ?)", [discord_id, main.char_id])

        return f"You have been linked with discord user <highlight>{discord_id}</highlight> successfully."

    @command(command="discord", params=[Const("getinvite"), Int("server_id")], access_level="member",
             description="Get an invite for specified server", sub_command="getinvite")
    def discord_getinvite_cmd(self, request, _, server_id):
        if self.client and self.client.guilds:
            for server in self.client.guilds:
                if server.id == server_id:
                    self.send_to_discord("get_invite", (request.sender.name, server))
                    return
        return f"Could not find Discord server with ID <highlight>{server_id}</highlight>."

    @timerevent(budatime="1s", description="Discord relay queue handler", is_system=True)
    def handle_discord_queue_event(self, event_type, event_data):
        if self.dqueue:
            dtype, message = self.dqueue.pop(0)

            if dtype == "discord_message":
                if message.channel.type == ChannelType.private or message.content.startswith(self.setting_service.get("symbol").get_value()):
                    self.handle_discord_command_event(message)
                else:
                    self.handle_discord_message_event(message)
            elif dtype == "discord_ready":
                self.send_to_discord("msg", DiscordTextMessage(f"{self.bot.get_primary_conn().get_char_name()} is now connected."))

            self.event_service.fire_event(dtype, message)

    @timerevent(budatime="1m", description="Ensure the bot is connected to Discord", is_enabled=False, is_system=True, run_at_startup=True)
    def handle_connect_event(self, event_type, event_data):
        if not self.is_connected():
            self.connect_discord_client()

    @event(event_type=AltsService.MAIN_CHANGED_EVENT_TYPE, description="Update discord character link when a main is changed", is_system=True)
    def handle_main_changed(self, event_type, event_data):
        old_row = self.db.query_single("SELECT discord_id FROM discord_char_link WHERE char_id = ?", [event_data.old_main_id])
        if old_row:
            new_row = self.db.query_single("SELECT discord_id FROM discord_char_link WHERE char_id = ?", [event_data.new_main_id])
            if not new_row:
                self.db.exec("INSERT INTO discord_char_link (discord_id, char_id) VALUES (?, ?)", [old_row.discord_id, event_data.new_main_id])

    @event(event_type="discord_invites", description="Handles invite requests", is_system=True)
    def handle_discord_invite_event(self, event_type, event_data):
        char_name = event_data[0]
        invites = event_data[1]

        t = int(time.time())

        blob = f"<header2>Available invites</header2>\n"
        if len(invites) > 0:
            for invite in invites:
                link = self.text.make_chatcmd("Join", "/start %s" % invite.url)
                timeleft = self.get_time_left(t, invite)
                used = str(invite.uses)
                useleft = "Unlimited" if invite.max_uses == 0 else (invite.max_uses - invite.uses)
                if invite.channel is not None:
                    channel = f" └ for channel: {invite.channel.name}"
                else:
                    channel = None

                blob += f"{invite.guild.name} [{link}]\n"
                blob += f" └ life time: {timeleft}\n"
                blob += f" └ used: {used}\n"
                blob += f" └ uses left: {useleft}\n"
                blob += f"{channel}\n\n"

        else:
            blob += "No invites currently exist."

        char_id = self.character_service.resolve_char_to_id(char_name)
        self.bot.send_private_message(char_id, ChatBlob("Discord invites", blob))

    def get_time_left(self, t, invite):
        if invite.max_age == 0:
            return "Permanent"

        created_at = int(invite.created_at.replace(tzinfo=timezone.utc).timestamp())
        expires_at = created_at + invite.max_age

        if expires_at < t:
            return "Expired"

        return self.util.time_to_readable(expires_at - t)

    def handle_discord_command_event(self, message):
        if not self.find_discord_command_handler(message):
            reply = partial(self.discord_command_reply, channel=message.channel)
            row = self.db.query_single("SELECT char_id FROM discord_char_link WHERE discord_id = ?", [message.author.id])
            if row:
                message_str = self.command_service.trim_command_symbol(message.content)
                self.command_service.process_command(message_str, self.COMMAND_CHANNEL, row.char_id, reply, self.bot.get_primary_conn())
            else:
                reply("You must use `!discord link &lt;your_ao_character&gt;` to link your Discord user to an AO character in order to access the full range of commands.")

    def handle_discord_message_event(self, message):
        if isinstance(message.author, Member):
            name = message.author.nick or message.author.name
        else:
            name = message.author.name

        chanclr = self.setting_service.get("relay_color_prefix")
        nameclr = self.setting_service.get("relay_color_name")
        mesgclr = self.setting_service.get("relay_color_message")

        formatted_message = "<grey>[</grey>%s<grey>]</grey> %s<grey>:</grey> %s" % (chanclr.format_text("Discord"), nameclr.format_text(name), mesgclr.format_text(message.content))

        self.message_hub_service.send_message(self.MESSAGE_SOURCE, None, None, formatted_message)

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
                self.send_to_discord("command_reply", DiscordEmbedMessage(page_title, page, msgcolor, channel))
            return

        if isinstance(content, DiscordMessage):
            self.send_to_discord("command_reply", content)
        else:
            self.logger.error("unable to process message for discord: " + content)

    def format_message(self, msg):
        msg = re.sub(r"<header>(.*?)</header>\n?", r"```less\n\1\n```", msg)
        msg = re.sub(r"<header2>(.*?)</header2>\n?", r"```yaml\n\1\n```", msg)
        msg = re.sub(r"<highlight>(.*?)</highlight>", r"`\1`", msg)
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
                self.setting_service.get("discord_channel_id").get_value(),
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
            self.client.loop.create_task(self.client.logout_with_message(
                f"{self.bot.get_primary_conn().get_char_name()} is disconnecting..."))
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

    def discord_link_cmd(self, ctx, reply, args):
        char = args[1]
        if not char.char_id:
            reply(StandardMessage.char_not_found(char.name))
            return

        main = self.alts_service.get_main(char.char_id)
        if main.char_id != char.char_id:
            reply("You cannot link an alt, you must link with a main character.")
            return

        author = ctx.message.author
        discord_user = "%s#%s (%d)" % (author.name, author.discriminator, author.id)
        confirm_link = self.text.make_tellcmd("Confirm", "discord confirm %d" % author.id)

        blob = f"Discord user {discord_user} would like to link to this character.\n\n"
        blob += "This discord user will inherit your access level on the bot so be sure that this is what you want to do.\n\n"
        blob += "If you are currently linked to another Discord user, this will replace that link.\n\n"
        blob += f"To confirm, click here: {confirm_link}"

        self.bot.send_private_message(char.char_id, ChatBlob("Discord Confirm Link", blob))

        reply(f"A confirmation has been sent to {char.name}. You must confirm the link from that character.")

    def discord_unlink_cmd(self, ctx, reply, args):
        self.db.exec("DELETE FROM discord_char_link WHERE discord_id = ?", [ctx.message.author.id])

        reply("You have successfully been unlinked from your AO character.")

    def is_connected(self):
        # not self.client or not self.dthread.is_alive()
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

        message = DiscordTextMessage(self.strip_html_tags(ctx.formatted_message))
        self.send_to_discord("msg", message)

    def get_text_channels(self):
        if self.client:
            return self.client.get_text_channels()
        else:
            return []

    def update_discord_channel(self, setting_name, old_value, new_value):
        if self.client:
            if not self.client.set_channel_id(new_value):
                self.logger.warning(f"Could not find discord channel '{new_value}'")

    def update_discord_state(self, setting_name, old_value, new_value):
        if setting_name == "discord_enabled":
            event_handlers = [self.handle_connect_event, self.handle_discord_queue_event, self.handle_discord_invite_event]
            for handler in event_handlers:
                event_handler = self.util.get_handler_name(handler)
                event_base_type, event_sub_type = self.event_service.get_event_type_parts(handler.event.event_type)
                self.event_service.update_event_status(event_base_type, event_sub_type, event_handler, 1 if new_value else 0)

            if not new_value:
                self.disconnect_discord_client()
